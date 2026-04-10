from __future__ import annotations

from pathlib import Path
from typing import Any

from ethics_prompt_rewrite.config import ExperimentConfig
from ethics_prompt_rewrite.data import LockedSplitStore
from ethics_prompt_rewrite.models import ExampleRecord, LabelSemantics, PredictionRecord
from ethics_prompt_rewrite.prompts import prompt_version_id, render_task_prompt
from ethics_prompt_rewrite.run_state import load_state, update_state
from ethics_prompt_rewrite.stats import compute_metrics, per_label_accuracy, slice_metrics
from ethics_prompt_rewrite.student import BaseStudentBackend
from ethics_prompt_rewrite.utils import chunked, read_json, read_jsonl, write_json, write_jsonl


def build_batches(examples: list[ExampleRecord], batch_size: int) -> list[list[ExampleRecord]]:
    return list(chunked(examples, batch_size))


def evaluate_batch(
    *,
    student: BaseStudentBackend,
    batch_examples: list[ExampleRecord],
    mutable_prompt: str,
    arm_name: str,
    split_name: str,
    config: ExperimentConfig,
    label_semantics: LabelSemantics,
    round_index: int | None = None,
    batch_index: int | None = None,
) -> list[PredictionRecord]:
    prompts = [
        render_task_prompt(
            wrapper_template=config.prompts.wrapper_template,
            mutable_prompt=mutable_prompt,
            scenario=example.scenario,
            label_semantics=label_semantics,
        )
        for example in batch_examples
    ]
    outputs = student.predict(prompts)
    version = prompt_version_id(mutable_prompt)
    records: list[PredictionRecord] = []
    for example, output in zip(batch_examples, outputs, strict=True):
        predicted_label = output.predicted_label
        is_correct = predicted_label == example.label if predicted_label is not None else False
        records.append(
            PredictionRecord(
                split_name=split_name,
                arm_name=arm_name,
                example_id=example.example_id,
                group_id=example.group_id,
                source_split=example.source_split,
                length_bucket=example.length_bucket,
                true_label=example.label,
                predicted_label=predicted_label,
                is_invalid=output.is_invalid,
                is_correct=is_correct,
                prompt_version=version,
                prompt_text=mutable_prompt,
                round_index=round_index,
                batch_index=batch_index,
                score_0=output.score_0,
                score_1=output.score_1,
                raw_output=output.raw_output,
            )
        )
    return records


def evaluate_examples(
    *,
    student: BaseStudentBackend,
    examples: list[ExampleRecord],
    mutable_prompt: str,
    arm_name: str,
    split_name: str,
    config: ExperimentConfig,
    label_semantics: LabelSemantics,
    batch_size: int,
    round_index: int | None = None,
) -> tuple[list[PredictionRecord], list[dict[str, Any]]]:
    all_records: list[PredictionRecord] = []
    batch_metrics: list[dict[str, Any]] = []
    for batch_index, batch in enumerate(build_batches(examples, batch_size)):
        batch_records = evaluate_batch(
            student=student,
            batch_examples=batch,
            mutable_prompt=mutable_prompt,
            arm_name=arm_name,
            split_name=split_name,
            config=config,
            label_semantics=label_semantics,
            round_index=round_index,
            batch_index=batch_index,
        )
        all_records.extend(batch_records)
        metrics = compute_metrics(batch_records)
        batch_metrics.append({"batch_index": batch_index, **metrics})
    return all_records, batch_metrics


def save_prediction_bundle(
    *,
    records: list[PredictionRecord],
    path: Path,
    metrics_path: Path,
) -> dict[str, Any]:
    write_jsonl(path, [record.model_dump(mode="json") for record in records])
    metrics = compute_metrics(records)
    write_json(
        metrics_path,
        {
            "overall": metrics,
            "per_label": per_label_accuracy(records),
            "per_length_bucket": slice_metrics(records, "length_bucket"),
            "per_source_split": slice_metrics(records, "source_split"),
        },
    )
    return metrics


def load_prediction_records(path: Path) -> list[PredictionRecord]:
    return [PredictionRecord(**row) for row in read_jsonl(path)]


def run_final_evaluation(
    *,
    config: ExperimentConfig,
    run_root: Path,
    store: LockedSplitStore,
    student: BaseStudentBackend,
    label_semantics: LabelSemantics,
    final_prompts: dict[str, str],
) -> dict[str, dict[str, Any]]:
    state = load_state(run_root)
    if state.get("final_test_evaluated"):
        metrics_dir = run_root / "final_evaluation" / "metrics"
        return {arm_name: read_json(metrics_dir / f"{arm_name}.json") for arm_name in final_prompts}
    update_state(
        run_root,
        adaptation_complete=True,
        current_phase="final_evaluation",
        final_test_unlocked=True,
    )
    final_examples = store.load_split("final_test", phase="final_evaluation", allow_final_test=True)
    predictions_dir = run_root / "final_evaluation" / "predictions"
    metrics_dir = run_root / "final_evaluation" / "metrics"
    predictions_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict[str, Any]] = {}
    for arm_name, prompt_text in final_prompts.items():
        records, _ = evaluate_examples(
            student=student,
            examples=final_examples,
            mutable_prompt=prompt_text,
            arm_name=arm_name,
            split_name="final_test",
            config=config,
            label_semantics=label_semantics,
            batch_size=config.student.batch_size,
        )
        metrics = save_prediction_bundle(
            records=records,
            path=predictions_dir / f"{arm_name}.jsonl",
            metrics_path=metrics_dir / f"{arm_name}.json",
        )
        results[arm_name] = metrics
    update_state(run_root, final_test_evaluated=True)
    return results
