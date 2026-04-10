from __future__ import annotations

from pathlib import Path
from typing import Any

from ethics_prompt_rewrite.adaptation import run_adaptation
from ethics_prompt_rewrite.config import ExperimentConfig, config_to_dict
from ethics_prompt_rewrite.data import (
    LockedSplitStore,
    load_label_semantics,
    prepare_dataset,
    split_paths,
)
from ethics_prompt_rewrite.evaluation import run_final_evaluation
from ethics_prompt_rewrite.reporting import analyze_seed_results, generate_final_report
from ethics_prompt_rewrite.run_state import update_state
from ethics_prompt_rewrite.student import build_student_backend
from ethics_prompt_rewrite.teacher import GeminiTeacher
from ethics_prompt_rewrite.utils import describe_environment, set_global_seed, write_json


def run_root_for_seed(config: ExperimentConfig, seed: int, *, smoke: bool) -> Path:
    name = f"smoke_seed_{seed}" if smoke else f"seed_{seed}"
    root = config.resolved_output_root() / "runs" / name
    root.mkdir(parents=True, exist_ok=True)
    return root


def _save_run_metadata(
    *,
    config: ExperimentConfig,
    run_root: Path,
    seed: int,
    student_metadata: dict[str, Any],
) -> None:
    write_json(run_root / "config_snapshot.json", config_to_dict(config))
    write_json(run_root / "environment.json", describe_environment())
    write_json(
        run_root / "runtime_metadata.json",
        {
            "seed": seed,
            "student": student_metadata,
            "teacher_model": config.teacher.model,
            "teacher_cache_dir": str(config.resolved_teacher_cache_dir()),
        },
    )


def run_single_seed(config: ExperimentConfig, *, seed: int, smoke: bool) -> dict[str, Any]:
    config.experiment.seed = seed
    set_global_seed(seed)
    run_root = run_root_for_seed(config, seed, smoke=smoke)
    prepare_dataset(config, seed=seed, run_root=run_root)
    store = LockedSplitStore(run_root)
    label_semantics = load_label_semantics(run_root)
    student = build_student_backend(config)
    teacher = GeminiTeacher(config)
    _save_run_metadata(
        config=config,
        run_root=run_root,
        seed=seed,
        student_metadata=student.metadata(),
    )
    update_state(run_root, current_phase="adaptation")
    final_prompts = run_adaptation(
        config=config,
        run_root=run_root,
        store=store,
        student=student,
        teacher=teacher,
        label_semantics=label_semantics,
    )
    write_json(run_root / "final_prompts.json", final_prompts)
    run_final_evaluation(
        config=config,
        run_root=run_root,
        store=store,
        student=student,
        label_semantics=label_semantics,
        final_prompts=final_prompts,
    )
    result = analyze_seed_results(config, run_root, seed)
    write_json(run_root / "split_paths.json", split_paths(run_root).model_dump(mode="json"))
    return result


def run_seed_suite(
    config: ExperimentConfig, *, seeds: list[int], smoke: bool = False
) -> list[dict[str, Any]]:
    results = [run_single_seed(config, seed=seed, smoke=smoke) for seed in seeds]
    generate_final_report(
        config=config,
        project_root=config.project_root,
        seed_summaries=results,
        run_roots=[run_root_for_seed(config, seed, smoke=smoke) for seed in seeds],
    )
    return results
