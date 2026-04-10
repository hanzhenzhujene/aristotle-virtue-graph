from __future__ import annotations

from pathlib import Path
from typing import Any

from ethics_prompt_rewrite.config import ExperimentConfig
from ethics_prompt_rewrite.data import LockedSplitStore
from ethics_prompt_rewrite.evaluation import (
    build_batches,
    evaluate_batch,
    evaluate_examples,
    save_prediction_bundle,
)
from ethics_prompt_rewrite.models import (
    ExampleRecord,
    LabelSemantics,
    PredictionRecord,
    RoundRecord,
    TeacherBatchExample,
)
from ethics_prompt_rewrite.stats import compute_metrics
from ethics_prompt_rewrite.student import BaseStudentBackend
from ethics_prompt_rewrite.teacher import GeminiTeacher
from ethics_prompt_rewrite.utils import read_json, sliding_average, write_json

ARM_EMPTY = "empty_prompt"
ARM_FIXED = "researcher_fixed_prompt"
ARM_SINGLE = "teacher_single_rewrite_prompt"
ARM_ITERATIVE = "teacher_multi_round_iterative_prompt"


def _arm_paths(run_root: Path, arm_name: str) -> tuple[Path, Path]:
    predictions_path = run_root / "selector_dev" / "predictions" / f"{arm_name}.jsonl"
    metrics_path = run_root / "selector_dev" / "metrics" / f"{arm_name}.json"
    predictions_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    return predictions_path, metrics_path


def _save_prompt(run_root: Path, arm_name: str, prompt_text: str) -> Path:
    path = run_root / "prompt_versions" / f"{arm_name}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt_text, encoding="utf-8")
    return path


def _load_saved_prompt(run_root: Path, arm_name: str) -> str | None:
    path = run_root / "prompt_versions" / f"{arm_name}.txt"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _teacher_payload(
    *,
    config: ExperimentConfig,
    current_prompt: str,
    task_wrapper: str,
    batch_examples: list[TeacherBatchExample],
    prompt_history: list[str],
) -> dict[str, Any]:
    return {
        "task_definition": {
            "immutable_wrapper": task_wrapper,
            "teacher_can_edit_only": "mutable_prompt",
            "output_requirement": "Return exactly one digit, 0 or 1.",
        },
        "current_prompt": current_prompt,
        "prompt_history": prompt_history[-5:],
        "max_prompt_chars": config.teacher.max_prompt_chars,
        "batch_examples": [example.model_dump(mode="json") for example in batch_examples],
    }


def _selector_summary_path(run_root: Path) -> Path:
    return run_root / "selector_dev" / "iterative_rounds.json"


def _load_rounds(run_root: Path) -> list[RoundRecord]:
    path = _selector_summary_path(run_root)
    if not path.exists():
        return []
    return [RoundRecord(**row) for row in read_json(path)]


def _save_rounds(run_root: Path, rounds: list[RoundRecord]) -> None:
    path = _selector_summary_path(run_root)
    write_json(path, [round_record.model_dump(mode="json") for round_record in rounds])


def _materialize_arm(
    *,
    arm_name: str,
    prompt_text: str,
    selector_examples: list[ExampleRecord],
    student: BaseStudentBackend,
    config: ExperimentConfig,
    label_semantics: LabelSemantics,
    run_root: Path,
) -> None:
    predictions_path, metrics_path = _arm_paths(run_root, arm_name)
    if predictions_path.exists() and metrics_path.exists():
        return
    records, _ = evaluate_examples(
        student=student,
        examples=selector_examples,
        mutable_prompt=prompt_text,
        arm_name=arm_name,
        split_name="selector_dev",
        config=config,
        label_semantics=label_semantics,
        batch_size=config.adaptation.batch_size,
    )
    save_prediction_bundle(records=records, path=predictions_path, metrics_path=metrics_path)
    _save_prompt(run_root, arm_name, prompt_text)


def _build_teacher_batch_examples(
    batch_examples: list[ExampleRecord],
    records: list[PredictionRecord],
) -> list[TeacherBatchExample]:
    return [
        TeacherBatchExample(
            example_id=record.example_id,
            scenario=example.scenario,
            gold_label=record.true_label,
            predicted_label=record.predicted_label,
            is_correct=record.is_correct,
            is_invalid=record.is_invalid,
        )
        for example, record in zip(batch_examples, records, strict=True)
    ]


def run_adaptation(
    *,
    config: ExperimentConfig,
    run_root: Path,
    store: LockedSplitStore,
    student: BaseStudentBackend,
    teacher: GeminiTeacher,
    label_semantics: LabelSemantics,
) -> dict[str, str]:
    teacher_examples = store.load_split("teacher_dev", phase="adaptation")
    selector_examples = store.load_split("selector_dev", phase="adaptation")

    empty_prompt = ""
    fixed_prompt = config.prompts.fixed_prompt
    task_wrapper = config.prompts.wrapper_template

    _materialize_arm(
        arm_name=ARM_EMPTY,
        prompt_text=empty_prompt,
        selector_examples=selector_examples,
        student=student,
        config=config,
        label_semantics=label_semantics,
        run_root=run_root,
    )
    _materialize_arm(
        arm_name=ARM_FIXED,
        prompt_text=fixed_prompt,
        selector_examples=selector_examples,
        student=student,
        config=config,
        label_semantics=label_semantics,
        run_root=run_root,
    )

    single_prompt = _load_saved_prompt(run_root, ARM_SINGLE)
    teacher_batches = build_batches(teacher_examples, config.adaptation.batch_size)
    selector_batches = build_batches(selector_examples, config.adaptation.batch_size)
    if single_prompt is None:
        first_teacher_batch = teacher_batches[0]
        first_records = evaluate_batch(
            student=student,
            batch_examples=first_teacher_batch,
            mutable_prompt=fixed_prompt,
            arm_name=ARM_SINGLE,
            split_name="teacher_dev",
            config=config,
            label_semantics=label_semantics,
            round_index=0,
            batch_index=0,
        )
        teacher_payload = _teacher_payload(
            config=config,
            current_prompt=fixed_prompt,
            task_wrapper=task_wrapper,
            batch_examples=_build_teacher_batch_examples(first_teacher_batch, first_records),
            prompt_history=[fixed_prompt],
        )
        response, cache_path = teacher.revise_prompt(teacher_payload)
        write_json(
            run_root / "teacher_outputs" / "single_rewrite.json", {"cache_path": str(cache_path)}
        )
        single_prompt = response.revised_prompt
        _save_prompt(run_root, ARM_SINGLE, single_prompt)
    _materialize_arm(
        arm_name=ARM_SINGLE,
        prompt_text=single_prompt,
        selector_examples=selector_examples,
        student=student,
        config=config,
        label_semantics=label_semantics,
        run_root=run_root,
    )

    iterative_prompt = _load_saved_prompt(run_root, ARM_ITERATIVE)
    saved_rounds = _load_rounds(run_root)
    if iterative_prompt is None or not saved_rounds:
        current_prompt = fixed_prompt
        prompt_history = [fixed_prompt]
        rounds: list[RoundRecord] = []
        iterative_selector_records = []
        selector_accuracies: list[float] = []
        best_prompt = fixed_prompt
        best_score = float("-inf")
        no_improvement = 0
        max_rounds = min(config.adaptation.max_rounds, len(teacher_batches), len(selector_batches))
        for round_index in range(max_rounds):
            teacher_records = evaluate_batch(
                student=student,
                batch_examples=teacher_batches[round_index],
                mutable_prompt=current_prompt,
                arm_name=ARM_ITERATIVE,
                split_name="teacher_dev",
                config=config,
                label_semantics=label_semantics,
                round_index=round_index,
                batch_index=round_index,
            )
            payload = _teacher_payload(
                config=config,
                current_prompt=current_prompt,
                task_wrapper=task_wrapper,
                batch_examples=_build_teacher_batch_examples(
                    teacher_batches[round_index], teacher_records
                ),
                prompt_history=prompt_history,
            )
            response, cache_path = teacher.revise_prompt(payload)
            selector_records = evaluate_batch(
                student=student,
                batch_examples=selector_batches[round_index],
                mutable_prompt=response.revised_prompt,
                arm_name=ARM_ITERATIVE,
                split_name="selector_dev",
                config=config,
                label_semantics=label_semantics,
                round_index=round_index,
                batch_index=round_index,
            )
            iterative_selector_records.extend(selector_records)
            selector_metrics = compute_metrics(selector_records)
            selector_accuracies.append(float(selector_metrics["accuracy"]))
            moving_average = sliding_average(
                selector_accuracies,
                config.adaptation.moving_average_window,
            )[-1]
            min_delta = config.adaptation.min_delta_pp / 100.0
            improved = moving_average >= best_score + min_delta
            if improved:
                best_score = moving_average
                best_prompt = response.revised_prompt
                no_improvement = 0
            elif len(selector_accuracies) >= config.adaptation.moving_average_window:
                no_improvement += 1
            round_record = RoundRecord(
                round_index=round_index,
                teacher_batch_index=round_index,
                selector_batch_index=round_index,
                teacher_prompt_before=current_prompt,
                teacher_prompt_after=response.revised_prompt,
                selector_accuracy=float(selector_metrics["accuracy"]),
                selector_invalid_rate=float(selector_metrics["invalid_output_rate"]),
                selector_moving_average=float(moving_average),
                improved_over_best=improved,
                teacher_response_path=cache_path,
            )
            rounds.append(round_record)
            prompt_history.append(response.revised_prompt)
            current_prompt = response.revised_prompt
            if no_improvement >= config.adaptation.patience:
                rounds[-1].stop_reason = "selector_moving_average_plateau"
                break
        iterative_prompt = best_prompt
        _save_rounds(run_root, rounds)
        _save_prompt(run_root, ARM_ITERATIVE, iterative_prompt)

        selector_prediction_path, selector_metrics_path = _arm_paths(run_root, ARM_ITERATIVE)
        if not selector_prediction_path.exists():
            save_prediction_bundle(
                records=iterative_selector_records,
                path=selector_prediction_path,
                metrics_path=selector_metrics_path,
            )

    return {
        ARM_EMPTY: empty_prompt,
        ARM_FIXED: fixed_prompt,
        ARM_SINGLE: single_prompt,
        ARM_ITERATIVE: iterative_prompt,
    }
