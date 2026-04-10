from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, cast

import matplotlib.pyplot as plt
import pandas as pd

from ethics_prompt_rewrite.adaptation import ARM_EMPTY, ARM_FIXED, ARM_ITERATIVE, ARM_SINGLE
from ethics_prompt_rewrite.config import ExperimentConfig
from ethics_prompt_rewrite.evaluation import load_prediction_records
from ethics_prompt_rewrite.models import PredictionRecord
from ethics_prompt_rewrite.stats import (
    bootstrap_accuracy_difference,
    compute_metrics,
    holm_bonferroni,
    mcnemar_exact,
)
from ethics_prompt_rewrite.utils import read_json, write_json

ARM_ORDER = [ARM_EMPTY, ARM_FIXED, ARM_SINGLE, ARM_ITERATIVE]


def _final_prediction_paths(run_root: Path) -> dict[str, Path]:
    return {
        arm_name: run_root / "final_evaluation" / "predictions" / f"{arm_name}.jsonl"
        for arm_name in ARM_ORDER
    }


def _teacher_round_failure_modes(run_root: Path) -> list[str]:
    rounds_path = run_root / "selector_dev" / "iterative_rounds.json"
    if not rounds_path.exists():
        return []
    rounds = read_json(rounds_path)
    failures: list[str] = []
    for row in rounds:
        cache_path = Path(row["teacher_response_path"])
        if not cache_path.exists():
            continue
        payload = read_json(cache_path)
        failures.extend(payload["response"].get("failure_modes", []))
    return failures


def _metrics_path(run_root: Path, arm_name: str) -> Path:
    return run_root / "final_evaluation" / "metrics" / f"{arm_name}.json"


def _load_arm_metrics(run_root: Path, arm_name: str) -> dict[str, Any]:
    return cast(dict[str, Any], read_json(_metrics_path(run_root, arm_name)))


def _weighted_slice_accuracy(
    run_roots: list[Path],
    *,
    arm_names: list[str],
    slice_key: str,
) -> pd.DataFrame:
    totals: dict[tuple[str, str], tuple[float, float]] = {}
    for run_root in run_roots:
        for arm_name in arm_names:
            payload = _load_arm_metrics(run_root, arm_name)
            for bucket, metrics in payload.get(slice_key, {}).items():
                count = float(metrics["count"])
                accuracy = float(metrics["accuracy"])
                current_weight, current_total = totals.get((bucket, arm_name), (0.0, 0.0))
                totals[(bucket, arm_name)] = (
                    current_weight + count,
                    current_total + accuracy * count,
                )
    buckets = sorted({bucket for bucket, _ in totals})
    rows: list[dict[str, Any]] = []
    for bucket in buckets:
        row: dict[str, Any] = {"slice": bucket}
        for arm_name in arm_names:
            weight, total = totals.get((bucket, arm_name), (0.0, 0.0))
            row[arm_name] = round(total / weight, 4) if weight else "n/a"
        rows.append(row)
    return pd.DataFrame(rows)


def _iterative_round_details(run_root: Path) -> list[dict[str, Any]]:
    rounds_path = run_root / "selector_dev" / "iterative_rounds.json"
    if not rounds_path.exists():
        return []
    rows = read_json(rounds_path)
    details: list[dict[str, Any]] = []
    for row in rows:
        change_summary: list[str] = []
        failure_modes: list[str] = []
        cache_path = Path(row["teacher_response_path"])
        if cache_path.exists():
            payload = read_json(cache_path)
            change_summary = payload["response"].get("change_summary", [])
            failure_modes = payload["response"].get("failure_modes", [])
        details.append(
            {
                "round": row["round_index"],
                "selector_accuracy": round(float(row["selector_accuracy"]), 4),
                "moving_average": round(float(row["selector_moving_average"]), 4),
                "improved": bool(row["improved_over_best"]),
                "failure_modes": ", ".join(failure_modes) or "none recorded",
                "change_summary": ", ".join(change_summary) or "none recorded",
                "prompt": row["teacher_prompt_after"],
            }
        )
    return details


def analyze_seed_results(config: ExperimentConfig, run_root: Path, seed: int) -> dict[str, Any]:
    prediction_records: dict[str, list[PredictionRecord]] = {
        arm_name: load_prediction_records(path)
        for arm_name, path in _final_prediction_paths(run_root).items()
    }
    metrics = {
        arm_name: compute_metrics(records) for arm_name, records in prediction_records.items()
    }
    primary = mcnemar_exact(prediction_records[ARM_ITERATIVE], prediction_records[ARM_SINGLE])
    secondary_raw = {
        f"{ARM_ITERATIVE}_vs_{ARM_FIXED}": mcnemar_exact(
            prediction_records[ARM_ITERATIVE],
            prediction_records[ARM_FIXED],
        )["p_value"],
        f"{ARM_ITERATIVE}_vs_{ARM_EMPTY}": mcnemar_exact(
            prediction_records[ARM_ITERATIVE],
            prediction_records[ARM_EMPTY],
        )["p_value"],
    }
    secondary_adjusted = holm_bonferroni(secondary_raw)
    pairwise = {
        f"{ARM_ITERATIVE}_vs_{ARM_SINGLE}": {
            **primary,
            "bootstrap_accuracy_diff": bootstrap_accuracy_difference(
                prediction_records[ARM_ITERATIVE],
                prediction_records[ARM_SINGLE],
                n_samples=config.experiment.bootstrap_samples,
                seed=seed,
            ),
        },
        f"{ARM_ITERATIVE}_vs_{ARM_FIXED}": {
            **mcnemar_exact(prediction_records[ARM_ITERATIVE], prediction_records[ARM_FIXED]),
            "holm_adjusted_p_value": secondary_adjusted[f"{ARM_ITERATIVE}_vs_{ARM_FIXED}"],
            "bootstrap_accuracy_diff": bootstrap_accuracy_difference(
                prediction_records[ARM_ITERATIVE],
                prediction_records[ARM_FIXED],
                n_samples=config.experiment.bootstrap_samples,
                seed=seed + 1000,
            ),
        },
        f"{ARM_ITERATIVE}_vs_{ARM_EMPTY}": {
            **mcnemar_exact(prediction_records[ARM_ITERATIVE], prediction_records[ARM_EMPTY]),
            "holm_adjusted_p_value": secondary_adjusted[f"{ARM_ITERATIVE}_vs_{ARM_EMPTY}"],
            "bootstrap_accuracy_diff": bootstrap_accuracy_difference(
                prediction_records[ARM_ITERATIVE],
                prediction_records[ARM_EMPTY],
                n_samples=config.experiment.bootstrap_samples,
                seed=seed + 2000,
            ),
        },
    }
    failure_modes = _teacher_round_failure_modes(run_root)
    failure_mode_counts = dict(Counter(failure_modes).most_common())

    _plot_seed_accuracy(run_root, metrics)
    _plot_round_history(run_root)

    output = {
        "seed": seed,
        "metrics": metrics,
        "pairwise_tests": pairwise,
        "failure_mode_counts": failure_mode_counts,
    }
    write_json(run_root / "final_evaluation" / "statistics.json", output)
    return output


def _plot_seed_accuracy(run_root: Path, metrics: dict[str, dict[str, Any]]) -> None:
    figure_path = run_root / "final_evaluation" / "accuracy_by_arm.png"
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    labels = ARM_ORDER
    values = [metrics[label]["accuracy"] for label in labels]
    plt.figure(figsize=(8, 4.5))
    plt.bar(labels, values, color=["#9ecae1", "#6baed6", "#3182bd", "#08519c"])
    plt.ylim(0.0, 1.0)
    plt.ylabel("Accuracy")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(figure_path, dpi=180)
    plt.close()


def _plot_round_history(run_root: Path) -> None:
    rounds_path = run_root / "selector_dev" / "iterative_rounds.json"
    if not rounds_path.exists():
        return
    rounds = pd.DataFrame(read_json(rounds_path))
    if rounds.empty:
        return
    figure_path = run_root / "selector_dev" / "iterative_round_history.png"
    plt.figure(figsize=(8, 4.5))
    plt.plot(
        rounds["round_index"],
        rounds["selector_accuracy"],
        marker="o",
        label="selector batch accuracy",
    )
    plt.plot(
        rounds["round_index"],
        rounds["selector_moving_average"],
        marker="s",
        label="moving average",
    )
    plt.ylim(0.0, 1.0)
    plt.xlabel("Round")
    plt.ylabel("Accuracy")
    plt.legend()
    plt.tight_layout()
    plt.savefig(figure_path, dpi=180)
    plt.close()


def generate_final_report(
    *,
    config: ExperimentConfig,
    project_root: Path,
    seed_summaries: list[dict[str, Any]],
    run_roots: list[Path] | None = None,
) -> Path:
    report_path = project_root / "reports" / "final_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    run_roots = run_roots or []
    summary_rows = []
    for summary in seed_summaries:
        row = {"seed": summary["seed"]}
        for arm_name in ARM_ORDER:
            row[f"{arm_name}_accuracy"] = summary["metrics"][arm_name]["accuracy"]
        summary_rows.append(row)
    summary_frame = pd.DataFrame(summary_rows)

    mean_metrics = {
        arm_name: float(summary_frame[f"{arm_name}_accuracy"].mean()) for arm_name in ARM_ORDER
    }
    iterative_gain_fixed = mean_metrics[ARM_ITERATIVE] - mean_metrics[ARM_FIXED]
    iterative_gain_empty = mean_metrics[ARM_ITERATIVE] - mean_metrics[ARM_EMPTY]
    iterative_gain_single = mean_metrics[ARM_ITERATIVE] - mean_metrics[ARM_SINGLE]
    iterative_outcome = (
        "outperformed"
        if iterative_gain_fixed > 0 and iterative_gain_empty > 0 and iterative_gain_single > 0
        else "did not cleanly outperform"
    )
    stable_phrase = (
        "stability was estimated across multiple seeds"
        if len(seed_summaries) > 1
        else "stability across seeds could not be established because only one full seed completed"
    )

    failure_counter: Counter[str] = Counter()
    for summary in seed_summaries:
        failure_counter.update(summary.get("failure_mode_counts", {}))
    common_failures = (
        ", ".join(failure for failure, _ in failure_counter.most_common(5)) or "none observed"
    )

    def markdown_table(frame: pd.DataFrame) -> str:
        headers = list(frame.columns)
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        for _, row in frame.iterrows():
            lines.append("| " + " | ".join(str(row[column]) for column in headers) + " |")
        return "\n".join(lines)

    per_label_table = (
        markdown_table(
            _weighted_slice_accuracy(
                run_roots,
                arm_names=ARM_ORDER,
                slice_key="per_label",
            )
        )
        if run_roots
        else None
    )
    per_length_table = (
        markdown_table(
            _weighted_slice_accuracy(
                run_roots,
                arm_names=[ARM_FIXED, ARM_ITERATIVE],
                slice_key="per_length_bucket",
            )
        )
        if run_roots
        else None
    )
    per_source_table = (
        markdown_table(
            _weighted_slice_accuracy(
                run_roots,
                arm_names=[ARM_FIXED, ARM_ITERATIVE],
                slice_key="per_source_split",
            )
        )
        if run_roots
        else None
    )
    round_details = _iterative_round_details(run_roots[0]) if run_roots else []
    final_prompt_lines: list[str] = []
    if run_roots:
        final_prompts = read_json(run_roots[0] / "final_prompts.json")
        for arm_name in ARM_ORDER:
            final_prompt_lines.append(f"- `{arm_name}`: {final_prompts[arm_name]}")

    lines = [
        "# Final Report",
        "",
        "## Research Question",
        "",
        (
            "Can a strong Gemini teacher improve a local Qwen-0.5B student on "
            "ETHICS commonsense moral judgment through iterative prompt rewriting "
            "based on batch-level error feedback alone?"
        ),
        "",
        "## Final-Test Accuracy",
        "",
        markdown_table(summary_frame),
        "",
        "## Direct Answers",
        "",
        (
            "1. Iterative prompt rewriting "
            f"{iterative_outcome} "
            "the fixed prompt, empty prompt, and single-rewrite prompt on average "
            "final-test accuracy across the completed seeds."
        ),
        (
            "2. Mean accuracy deltas for iterative prompting were "
            f"{iterative_gain_fixed:+.4f} vs fixed, "
            f"{iterative_gain_empty:+.4f} vs empty, and "
            f"{iterative_gain_single:+.4f} vs single-rewrite."
        ),
        f"3. {stable_phrase}.",
        f"4. The teacher most often targeted these failure themes: {common_failures}.",
        (
            "5. Main threats to validity: one benchmark subset only, prompt-level "
            "optimization on a single student family, possible residual dependence "
            "on how group-level stratification approximates the joint distribution, "
            "and limited seed count if fewer than three full seeds complete."
        ),
        "",
        "## Notes",
        "",
        (
            "- The primary statistical comparison is iterative vs single-rewrite "
            "on final_test using McNemar's exact test."
        ),
        "- Secondary pairwise p-values were Holm-adjusted.",
        "- The final test split stayed locked until the final evaluation step.",
    ]
    if per_label_table:
        lines.extend(
            [
                "",
                "## Post-hoc Slices",
                "",
                "Per-label weighted accuracy across completed runs:",
                "",
                per_label_table,
                "",
                "Iterative vs fixed weighted accuracy by length bucket:",
                "",
                per_length_table or "",
                "",
                "Iterative vs fixed weighted accuracy by original source split:",
                "",
                per_source_table or "",
            ]
        )
    if round_details:
        lines.extend(
            [
                "",
                "## Iterative Prompt History",
                "",
                "Final prompts from the first completed run:",
                "",
                *final_prompt_lines,
                "",
                "Round-by-round selector behavior for the first completed run:",
                "",
            ]
        )
        for detail in round_details:
            lines.extend(
                [
                    (
                        f"- Round {detail['round']}: selector accuracy "
                        f"{detail['selector_accuracy']:.4f}, moving average "
                        f"{detail['moving_average']:.4f}, improved={detail['improved']}."
                    ),
                    f"- Targeted failures: {detail['failure_modes']}.",
                    f"- Change summary: {detail['change_summary']}.",
                    f"- Prompt: {detail['prompt']}",
                ]
            )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
