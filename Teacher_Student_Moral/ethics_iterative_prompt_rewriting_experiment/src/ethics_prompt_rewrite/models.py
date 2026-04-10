from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ExampleRecord(BaseModel):
    example_id: str
    group_id: str
    scenario: str
    normalized_scenario: str
    label: int
    source_split: str
    source_row_index: int
    length_bucket: str
    token_length: int
    duplicate_group_size: int


class GroupRecord(BaseModel):
    group_id: str
    example_ids: list[str]
    size: int
    primary_label: int
    primary_source_split: str
    primary_length_bucket: str
    stratify_key: str = ""


class LabelSemantics(BaseModel):
    acceptable_label: int
    unacceptable_label: int
    evidence_source: str
    evidence_excerpt: str


class SplitPaths(BaseModel):
    all_examples: Path
    groups: Path
    development: Path
    teacher_dev: Path
    selector_dev: Path
    final_test_locked: Path
    summary: Path
    label_semantics: Path
    access_log: Path


class SplitSummary(BaseModel):
    dataset_name: str
    dataset_config: str
    source_split_counts: dict[str, int]
    partition_counts: dict[str, int]
    duplicate_group_count: int
    duplicate_example_count: int
    conflicting_duplicate_groups: list[str]
    label_counts: dict[str, int]
    stratification_level: str
    max_examples_applied: int | None = None
    original_total_examples: int


class PredictionRecord(BaseModel):
    split_name: str
    arm_name: str
    example_id: str
    group_id: str
    source_split: str
    length_bucket: str
    true_label: int
    predicted_label: int | None
    is_invalid: bool
    is_correct: bool
    prompt_version: str
    prompt_text: str
    round_index: int | None = None
    batch_index: int | None = None
    score_0: float | None = None
    score_1: float | None = None
    raw_output: str | None = None


class TeacherBatchExample(BaseModel):
    example_id: str
    scenario: str
    gold_label: int
    predicted_label: int | None
    is_correct: bool
    is_invalid: bool


class TeacherRevisionResponse(BaseModel):
    diagnosis_summary: str
    failure_modes: list[str]
    change_summary: list[str]
    revised_prompt: str = Field(min_length=1)


class RoundRecord(BaseModel):
    round_index: int
    teacher_batch_index: int
    selector_batch_index: int | None = None
    teacher_prompt_before: str
    teacher_prompt_after: str
    selector_accuracy: float | None = None
    selector_invalid_rate: float | None = None
    selector_moving_average: float | None = None
    improved_over_best: bool = False
    stop_reason: str | None = None
    teacher_response_path: Path | None = None


class RunSummary(BaseModel):
    seed: int
    smoke: bool
    student_backend: str
    student_identifier: str
    teacher_model: str
    final_prompts: dict[str, str]
    final_test_metrics: dict[str, dict[str, Any]]
