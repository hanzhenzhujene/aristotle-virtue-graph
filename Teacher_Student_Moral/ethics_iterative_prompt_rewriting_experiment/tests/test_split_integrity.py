from __future__ import annotations

from pathlib import Path

import pytest

from ethics_prompt_rewrite.adaptation import run_adaptation
from ethics_prompt_rewrite.config import ExperimentConfig
from ethics_prompt_rewrite.data import validate_partition_integrity
from ethics_prompt_rewrite.models import ExampleRecord, LabelSemantics, TeacherRevisionResponse


def _example(example_id: str, group_id: str, label: int) -> ExampleRecord:
    return ExampleRecord(
        example_id=example_id,
        group_id=group_id,
        scenario=f"Scenario {example_id}",
        normalized_scenario=f"scenario {example_id}",
        label=label,
        source_split="train",
        source_row_index=0,
        length_bucket="000_079",
        token_length=2,
        duplicate_group_size=1,
    )


def test_validate_partition_integrity_rejects_group_leakage() -> None:
    partitions = {
        "teacher_dev": [_example("a", "g1", 0)],
        "selector_dev": [_example("b", "g1", 1)],
        "final_test": [],
    }
    with pytest.raises(RuntimeError):
        validate_partition_integrity(partitions)


def test_validate_partition_integrity_allows_clean_partitions() -> None:
    partitions = {
        "teacher_dev": [_example("a", "g1", 0)],
        "selector_dev": [_example("b", "g2", 1)],
        "final_test": [_example("c", "g3", 0)],
    }
    validate_partition_integrity(partitions)


class DummyStudent:
    def predict(self, prompts: list[str]):
        from ethics_prompt_rewrite.student import StudentPrediction

        return [
            StudentPrediction(
                predicted_label=index % 2, is_invalid=False, raw_output=str(index % 2)
            )
            for index, _ in enumerate(prompts)
        ]


class DummyTeacher:
    def revise_prompt(self, payload):
        return TeacherRevisionResponse(
            diagnosis_summary="summary",
            failure_modes=["harm", "coercion"],
            change_summary=["be explicit"],
            revised_prompt="Judge the action as written. Prefer ordinary harm and consent cues.",
        ), Path("/tmp/teacher-cache.json")


class DummyStore:
    def __init__(self, teacher_dev: list[ExampleRecord], selector_dev: list[ExampleRecord]):
        self.teacher_dev = teacher_dev
        self.selector_dev = selector_dev
        self.requests: list[str] = []

    def load_split(self, split_name: str, *, phase: str, allow_final_test: bool = False):
        self.requests.append(split_name)
        if split_name == "teacher_dev":
            return self.teacher_dev
        if split_name == "selector_dev":
            return self.selector_dev
        raise AssertionError("final_test should not be loaded during adaptation")


def test_adaptation_does_not_load_final_test(tmp_path: Path) -> None:
    config = ExperimentConfig(
        experiment={
            "name": "x",
            "seed": 1,
            "seeds": [1],
            "bootstrap_samples": 10,
            "output_root": "outputs",
        },
        data={
            "dataset_name": "d",
            "dataset_config": "c",
            "final_test_fraction": 0.2,
            "teacher_dev_fraction_of_development": 0.75,
            "length_bucket_edges": [0, 10, 100],
        },
        student={"hf_model_id_or_path": "Qwen/Qwen2.5-0.5B-Instruct"},
        teacher={"model": "gemini-2.5-pro"},
        adaptation={
            "batch_size": 2,
            "max_rounds": 2,
            "min_delta_pp": 0.3,
            "patience": 1,
            "moving_average_window": 2,
        },
        prompts={
            "fixed_prompt": "Base prompt.",
            "wrapper_template": (
                "{mutable_prompt}\n\nScenario: {scenario}\n\nQuestion: ok?\n"
                "{acceptable_label}=ok\n{unacceptable_label}=bad\nAnswer:"
            ),
        },
        runtime={"teacher_cache_dir": "outputs/cache/teacher"},
        project_root=tmp_path,
    )
    store = DummyStore(
        teacher_dev=[_example("a", "g1", 0), _example("b", "g2", 1)],
        selector_dev=[_example("c", "g3", 0), _example("d", "g4", 1)],
    )
    prompts = run_adaptation(
        config=config,
        run_root=tmp_path,
        store=store,
        student=DummyStudent(),
        teacher=DummyTeacher(),
        label_semantics=LabelSemantics(
            acceptable_label=0,
            unacceptable_label=1,
            evidence_source="test",
            evidence_excerpt="",
        ),
    )
    assert "final_test" not in store.requests
    assert "teacher_multi_round_iterative_prompt" in prompts
