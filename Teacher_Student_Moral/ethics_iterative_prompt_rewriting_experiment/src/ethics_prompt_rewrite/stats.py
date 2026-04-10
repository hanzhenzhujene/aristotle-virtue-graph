from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
from scipy.stats import binomtest
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score, matthews_corrcoef

from ethics_prompt_rewrite.models import PredictionRecord


def _effective_prediction(record: PredictionRecord) -> int:
    if record.predicted_label is None:
        return 1 - record.true_label
    return record.predicted_label


def compute_metrics(records: list[PredictionRecord]) -> dict[str, Any]:
    if not records:
        return {
            "count": 0,
            "accuracy": 0.0,
            "balanced_accuracy": 0.0,
            "f1": 0.0,
            "mcc": 0.0,
            "invalid_output_rate": 0.0,
            "confusion_matrix": [[0, 0], [0, 0]],
        }
    y_true = np.array([record.true_label for record in records], dtype=int)
    y_pred = np.array([_effective_prediction(record) for record in records], dtype=int)
    invalid_rate = float(sum(record.is_invalid for record in records) / len(records))
    accuracy = float(np.mean(y_true == y_pred))
    return {
        "count": int(len(records)),
        "accuracy": accuracy,
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "mcc": float(matthews_corrcoef(y_true, y_pred)),
        "invalid_output_rate": invalid_rate,
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
    }


def slice_metrics(records: list[PredictionRecord], field_name: str) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[PredictionRecord]] = defaultdict(list)
    for record in records:
        buckets[str(getattr(record, field_name))].append(record)
    return {
        bucket: compute_metrics(bucket_records)
        for bucket, bucket_records in sorted(buckets.items())
    }


def per_label_accuracy(records: list[PredictionRecord]) -> dict[str, dict[str, float]]:
    buckets: dict[int, list[PredictionRecord]] = defaultdict(list)
    for record in records:
        buckets[record.true_label].append(record)
    result: dict[str, dict[str, float]] = {}
    for label, bucket in sorted(buckets.items()):
        effective = [_effective_prediction(record) for record in bucket]
        result[str(label)] = {
            "count": float(len(bucket)),
            "accuracy": float(
                np.mean(np.array([record.true_label for record in bucket]) == np.array(effective))
            ),
        }
    return result


def mcnemar_exact(
    records_a: list[PredictionRecord], records_b: list[PredictionRecord]
) -> dict[str, Any]:
    by_id_a = {record.example_id: record for record in records_a}
    by_id_b = {record.example_id: record for record in records_b}
    shared_ids = sorted(set(by_id_a) & set(by_id_b))
    b = 0
    c = 0
    for example_id in shared_ids:
        correct_a = by_id_a[example_id].is_correct
        correct_b = by_id_b[example_id].is_correct
        if correct_a and not correct_b:
            b += 1
        elif correct_b and not correct_a:
            c += 1
    total = b + c
    p_value = (
        1.0
        if total == 0
        else float(binomtest(min(b, c), total, 0.5, alternative="two-sided").pvalue)
    )
    return {
        "discordant_a_only": b,
        "discordant_b_only": c,
        "p_value": p_value,
    }


def holm_bonferroni(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    adjusted: dict[str, float] = {}
    total = len(ordered)
    running_max = 0.0
    for index, (name, p_value) in enumerate(ordered):
        factor = total - index
        candidate = min(1.0, p_value * factor)
        running_max = max(running_max, candidate)
        adjusted[name] = running_max
    return adjusted


def bootstrap_accuracy_difference(
    records_a: list[PredictionRecord],
    records_b: list[PredictionRecord],
    *,
    n_samples: int,
    seed: int,
) -> dict[str, float]:
    by_id_a = {record.example_id: record for record in records_a}
    by_id_b = {record.example_id: record for record in records_b}
    shared_ids = sorted(set(by_id_a) & set(by_id_b))
    if not shared_ids:
        return {"low": 0.0, "high": 0.0, "mean": 0.0}
    rng = np.random.default_rng(seed)
    deltas = []
    for _ in range(n_samples):
        sampled_ids = rng.choice(shared_ids, size=len(shared_ids), replace=True)
        accuracy_a = np.mean([by_id_a[item].is_correct for item in sampled_ids])
        accuracy_b = np.mean([by_id_b[item].is_correct for item in sampled_ids])
        deltas.append(float(accuracy_a - accuracy_b))
    array = np.array(deltas, dtype=float)
    return {
        "low": float(np.percentile(array, 2.5)),
        "high": float(np.percentile(array, 97.5)),
        "mean": float(array.mean()),
    }
