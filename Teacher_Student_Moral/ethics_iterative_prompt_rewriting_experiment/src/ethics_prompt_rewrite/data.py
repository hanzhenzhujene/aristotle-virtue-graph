from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

from datasets import DatasetDict, load_dataset, load_dataset_builder
from sklearn.model_selection import train_test_split

from ethics_prompt_rewrite.config import ExperimentConfig
from ethics_prompt_rewrite.models import (
    ExampleRecord,
    GroupRecord,
    LabelSemantics,
    SplitPaths,
    SplitSummary,
)
from ethics_prompt_rewrite.run_state import load_state
from ethics_prompt_rewrite.utils import (
    normalize_text,
    read_json,
    read_jsonl,
    set_global_seed,
    sha256_text,
    utc_now_iso,
    write_json,
    write_jsonl,
)

SCENARIO_FIELD_CANDIDATES = ("input", "scenario", "text")
LABEL_FIELD_CANDIDATES = ("label", "labels")


def split_paths(run_root: Path) -> SplitPaths:
    data_root = run_root / "data"
    return SplitPaths(
        all_examples=data_root / "all_examples.jsonl",
        groups=data_root / "duplicate_groups.jsonl",
        development=data_root / "development.jsonl",
        teacher_dev=data_root / "teacher_dev.jsonl",
        selector_dev=data_root / "selector_dev.jsonl",
        final_test_locked=data_root / "locked_final_test" / "final_test.jsonl",
        summary=data_root / "split_summary.json",
        label_semantics=data_root / "label_semantics.json",
        access_log=data_root / "access_log.jsonl",
    )


def _detect_field_name(columns: list[str], candidates: tuple[str, ...], kind: str) -> str:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    msg = f"Could not find a {kind} field in dataset columns: {columns!r}"
    raise RuntimeError(msg)


def _bucket_length(token_length: int, edges: list[int]) -> str:
    for left, right in zip(edges, edges[1:], strict=True):
        if left <= token_length < right:
            return f"{left:03d}_{right - 1:03d}"
    return f"{edges[-1]:03d}_plus"


def _infer_label_semantics(description: str, feature_repr: str) -> LabelSemantics:
    text = f"{description}\n{feature_repr}"
    compact = " ".join(text.lower().split())
    patterns = [
        (
            re.compile(
                r"0\s*(?:=|means|is)\s*(?:morally\s+)?acceptable.*?1\s*(?:=|means|is)\s*(?:morally\s+)?unacceptable"
            ),
            (0, 1),
        ),
        (
            re.compile(
                r"1\s*(?:=|means|is)\s*(?:morally\s+)?unacceptable.*?0\s*(?:=|means|is)\s*(?:morally\s+)?acceptable"
            ),
            (0, 1),
        ),
        (
            re.compile(
                r"0\s*(?:=|means|is)\s*(?:morally\s+)?unacceptable.*?1\s*(?:=|means|is)\s*(?:morally\s+)?acceptable"
            ),
            (1, 0),
        ),
        (
            re.compile(
                r"1\s*(?:=|means|is)\s*(?:morally\s+)?acceptable.*?0\s*(?:=|means|is)\s*(?:morally\s+)?unacceptable"
            ),
            (1, 0),
        ),
    ]
    for pattern, (acceptable_label, unacceptable_label) in patterns:
        match = pattern.search(compact)
        if match:
            excerpt = compact[max(0, match.start() - 80) : match.end() + 80]
            return LabelSemantics(
                acceptable_label=acceptable_label,
                unacceptable_label=unacceptable_label,
                evidence_source="dataset_builder_info",
                evidence_excerpt=excerpt,
            )
    msg = (
        "Unable to infer label semantics from the loaded dataset metadata. "
        "The experiment refuses to guess because wrapper labels must be correct."
    )
    raise RuntimeError(msg)


def _infer_label_semantics_from_examples(records: list[ExampleRecord]) -> LabelSemantics:
    positive_patterns = [
        re.compile(r"\bi donated money to a charity\b"),
        re.compile(r"\bi donated a lot of money to the homeless shelter\b"),
        re.compile(r"\bi helped the small kitten who was crying out\b"),
        re.compile(r"\bi saved up to buy her the life-saving surgery\b"),
    ]
    negative_patterns = [
        re.compile(r"\bi stole money from the credit union\b"),
        re.compile(r"\bi killed the almost extinct birds to have for dinner\b"),
        re.compile(r"\bi lied to her about my address\b"),
        re.compile(r"\bblackmail later\b"),
    ]

    positive_hits: list[ExampleRecord] = []
    negative_hits: list[ExampleRecord] = []

    for record in records:
        text = record.normalized_scenario
        if any(pattern.search(text) for pattern in positive_patterns):
            positive_hits.append(record)
        if any(pattern.search(text) for pattern in negative_patterns):
            negative_hits.append(record)

    if not positive_hits or not negative_hits:
        msg = (
            "Unable to infer label semantics from metadata, and the example-based fallback "
            "did not find enough anchor scenarios."
        )
        raise RuntimeError(msg)

    positive_majority = Counter(hit.label for hit in positive_hits).most_common(1)[0][0]
    negative_majority = Counter(hit.label for hit in negative_hits).most_common(1)[0][0]
    if positive_majority == negative_majority:
        msg = (
            "Example-based label semantics inference was ambiguous because positive and "
            "negative anchors mapped to the same label."
        )
        raise RuntimeError(msg)

    evidence_lines = []
    for prefix, hits in (
        ("acceptable_anchor", positive_hits[:2]),
        ("unacceptable_anchor", negative_hits[:2]),
    ):
        for hit in hits:
            evidence_lines.append(f"{prefix}: label={hit.label} | {hit.scenario}")

    return LabelSemantics(
        acceptable_label=int(positive_majority),
        unacceptable_label=int(negative_majority),
        evidence_source="loaded_example_heuristic",
        evidence_excerpt="\n".join(evidence_lines),
    )


def _select_stratification_keys(groups: list[GroupRecord]) -> tuple[list[str] | None, str]:
    candidates = {
        "label_source_length": [
            f"{group.primary_label}|{group.primary_source_split}|{group.primary_length_bucket}"
            for group in groups
        ],
        "label_length": [
            f"{group.primary_label}|{group.primary_length_bucket}" for group in groups
        ],
        "label": [str(group.primary_label) for group in groups],
    }
    for name, values in candidates.items():
        counts = Counter(values)
        if all(count >= 2 for count in counts.values()):
            return values, name
    return None, "unstratified"


def _build_group_records(records: list[ExampleRecord]) -> tuple[list[GroupRecord], list[str]]:
    by_group: dict[str, list[ExampleRecord]] = defaultdict(list)
    for record in records:
        by_group[record.group_id].append(record)
    conflicting_groups: list[str] = []
    groups: list[GroupRecord] = []
    for group_id, group_examples in by_group.items():
        labels = Counter(example.label for example in group_examples)
        sources = Counter(example.source_split for example in group_examples)
        buckets = Counter(example.length_bucket for example in group_examples)
        if len(labels) > 1:
            conflicting_groups.append(group_id)
        group = GroupRecord(
            group_id=group_id,
            example_ids=[example.example_id for example in group_examples],
            size=len(group_examples),
            primary_label=labels.most_common(1)[0][0],
            primary_source_split=sources.most_common(1)[0][0],
            primary_length_bucket=buckets.most_common(1)[0][0],
        )
        groups.append(group)
    return sorted(groups, key=lambda item: item.group_id), conflicting_groups


def _partition_from_groups(
    groups: list[GroupRecord],
    *,
    test_fraction: float,
    seed: int,
) -> tuple[set[str], set[str], str]:
    group_ids = [group.group_id for group in groups]
    stratify_values, stratification_level = _select_stratification_keys(groups)
    train_groups, test_groups = train_test_split(
        group_ids,
        test_size=test_fraction,
        random_state=seed,
        shuffle=True,
        stratify=stratify_values,
    )
    return set(train_groups), set(test_groups), stratification_level


def _load_split_records(path: Path) -> list[ExampleRecord]:
    return [ExampleRecord(**row) for row in read_jsonl(path)]


def validate_partition_integrity(partitions: dict[str, list[ExampleRecord]]) -> None:
    if "development" in partitions:
        development_ids = {record.example_id for record in partitions["development"]}
        expected_ids = {
            record.example_id
            for split_name in ("teacher_dev", "selector_dev")
            for record in partitions.get(split_name, [])
        }
        if development_ids != expected_ids:
            msg = "development must equal the union of teacher_dev and selector_dev."
            raise RuntimeError(msg)

    seen_examples: dict[str, str] = {}
    group_assignments: dict[str, str] = {}
    for split_name, records in partitions.items():
        if split_name == "development":
            continue
        for record in records:
            previous_split = seen_examples.get(record.example_id)
            if previous_split is not None:
                msg = (
                    f"Example {record.example_id} appears in both "
                    f"{previous_split} and {split_name}."
                )
                raise RuntimeError(msg)
            seen_examples[record.example_id] = split_name

            previous_group_split = group_assignments.get(record.group_id)
            if previous_group_split is not None and previous_group_split != split_name:
                msg = (
                    f"Duplicate group {record.group_id} crosses "
                    f"{previous_group_split} and {split_name}."
                )
                raise RuntimeError(msg)
            group_assignments[record.group_id] = split_name


def prepare_dataset(config: ExperimentConfig, *, seed: int, run_root: Path) -> SplitPaths:
    paths = split_paths(run_root)
    if paths.summary.exists():
        return paths

    builder = load_dataset_builder(
        config.data.dataset_name,
        config.data.dataset_config,
        trust_remote_code=True,
    )
    dataset_dict = load_dataset(
        config.data.dataset_name,
        config.data.dataset_config,
        trust_remote_code=True,
    )
    if not isinstance(dataset_dict, DatasetDict):
        msg = "Expected a dataset dictionary with official splits."
        raise RuntimeError(msg)

    records: list[ExampleRecord] = []
    source_split_counts: dict[str, int] = {}
    original_total_examples = 0

    for source_split, split_dataset in dataset_dict.items():
        columns = list(split_dataset.column_names)
        scenario_field = _detect_field_name(columns, SCENARIO_FIELD_CANDIDATES, "scenario")
        label_field = _detect_field_name(columns, LABEL_FIELD_CANDIDATES, "label")
        source_split_counts[source_split] = len(split_dataset)
        for index, row in enumerate(split_dataset):
            original_total_examples += 1
            scenario = str(row[scenario_field]).strip()
            normalized = normalize_text(scenario, casefold=config.data.normalize_casefold)
            token_length = len(normalized.split())
            group_id = sha256_text(normalized)
            length_bucket = _bucket_length(token_length, config.data.length_bucket_edges)
            records.append(
                ExampleRecord(
                    example_id="",
                    group_id=group_id,
                    scenario=scenario,
                    normalized_scenario=normalized,
                    label=int(row[label_field]),
                    source_split=source_split,
                    source_row_index=index,
                    length_bucket=length_bucket,
                    token_length=token_length,
                    duplicate_group_size=0,
                )
            )

    try:
        label_semantics = _infer_label_semantics(
            description=builder.info.description or "",
            feature_repr=repr(builder.info.features),
        )
    except RuntimeError:
        label_semantics = _infer_label_semantics_from_examples(records)

    if config.data.max_examples is not None:
        set_global_seed(seed)
        records = sorted(
            records, key=lambda item: (item.group_id, item.source_split, item.source_row_index)
        )
        import random

        random.shuffle(records)
        records = records[: config.data.max_examples]

    grouped_examples: dict[str, list[ExampleRecord]] = defaultdict(list)
    for record in records:
        grouped_examples[record.group_id].append(record)

    finalized_records: list[ExampleRecord] = []
    for group_id in sorted(grouped_examples):
        group_examples = sorted(
            grouped_examples[group_id],
            key=lambda item: (item.source_split, item.source_row_index),
        )
        for index, record in enumerate(group_examples):
            updated = record.model_copy(
                update={
                    "example_id": f"{group_id[:16]}-{index:04d}",
                    "duplicate_group_size": len(group_examples),
                }
            )
            finalized_records.append(updated)

    groups, conflicting_groups = _build_group_records(finalized_records)
    development_groups, final_test_groups, stratification_level = _partition_from_groups(
        groups,
        test_fraction=config.data.final_test_fraction,
        seed=seed,
    )
    teacher_fraction = config.data.teacher_dev_fraction_of_development
    development_group_records = [group for group in groups if group.group_id in development_groups]
    teacher_dev_groups, selector_dev_groups, second_strat_level = _partition_from_groups(
        development_group_records,
        test_fraction=1.0 - teacher_fraction,
        seed=seed + 1,
    )

    partitioned: dict[str, list[ExampleRecord]] = {
        "development": [],
        "teacher_dev": [],
        "selector_dev": [],
        "final_test": [],
    }
    for record in finalized_records:
        if record.group_id in final_test_groups:
            partitioned["final_test"].append(record)
        elif record.group_id in teacher_dev_groups:
            partitioned["teacher_dev"].append(record)
            partitioned["development"].append(record)
        elif record.group_id in selector_dev_groups:
            partitioned["selector_dev"].append(record)
            partitioned["development"].append(record)
        else:
            msg = f"Example {record.example_id} was not assigned to any partition."
            raise RuntimeError(msg)

    validate_partition_integrity(partitioned)

    write_jsonl(
        paths.all_examples, [record.model_dump(mode="json") for record in finalized_records]
    )
    write_jsonl(paths.groups, [group.model_dump(mode="json") for group in groups])
    write_jsonl(
        paths.development, [record.model_dump(mode="json") for record in partitioned["development"]]
    )
    write_jsonl(
        paths.teacher_dev, [record.model_dump(mode="json") for record in partitioned["teacher_dev"]]
    )
    write_jsonl(
        paths.selector_dev,
        [record.model_dump(mode="json") for record in partitioned["selector_dev"]],
    )
    write_jsonl(
        paths.final_test_locked,
        [record.model_dump(mode="json") for record in partitioned["final_test"]],
    )
    write_json(
        paths.label_semantics,
        {
            **label_semantics.model_dump(mode="json"),
            "created_at": utc_now_iso(),
        },
    )

    summary = SplitSummary(
        dataset_name=config.data.dataset_name,
        dataset_config=config.data.dataset_config,
        source_split_counts=source_split_counts,
        partition_counts={key: len(value) for key, value in partitioned.items()},
        duplicate_group_count=sum(1 for group in groups if group.size > 1),
        duplicate_example_count=sum(group.size for group in groups if group.size > 1),
        conflicting_duplicate_groups=conflicting_groups,
        label_counts=dict(Counter(str(record.label) for record in finalized_records)),
        stratification_level=f"{stratification_level} -> {second_strat_level}",
        max_examples_applied=config.data.max_examples,
        original_total_examples=original_total_examples,
    )
    write_json(paths.summary, summary.model_dump(mode="json"))
    write_json(paths.access_log, {"events": []})
    return paths


class LockedSplitStore:
    def __init__(self, run_root: Path):
        self.run_root = run_root
        self.paths = split_paths(run_root)

    def _append_access(self, split_name: str, phase: str) -> None:
        existing: dict[str, list[dict[str, str]]] = {"events": []}
        if self.paths.access_log.exists():
            existing = read_json(self.paths.access_log)
        existing["events"].append(
            {"split_name": split_name, "phase": phase, "timestamp": utc_now_iso()}
        )
        write_json(self.paths.access_log, existing)

    def load_split(
        self, split_name: str, *, phase: str, allow_final_test: bool = False
    ) -> list[ExampleRecord]:
        path_lookup = {
            "development": self.paths.development,
            "teacher_dev": self.paths.teacher_dev,
            "selector_dev": self.paths.selector_dev,
            "final_test": self.paths.final_test_locked,
        }
        if split_name == "final_test":
            state = load_state(self.run_root)
            if (
                not allow_final_test
                or not state.get("adaptation_complete")
                or state.get("final_test_evaluated")
            ):
                msg = "final_test is locked until final evaluation and may only be unlocked once."
                raise PermissionError(msg)
        self._append_access(split_name, phase)
        path = path_lookup[split_name]
        return _load_split_records(path)


def load_label_semantics(run_root: Path) -> LabelSemantics:
    paths = split_paths(run_root)
    raw = read_json(paths.label_semantics)
    return LabelSemantics(
        acceptable_label=int(raw["acceptable_label"]),
        unacceptable_label=int(raw["unacceptable_label"]),
        evidence_source=str(raw["evidence_source"]),
        evidence_excerpt=str(raw["evidence_excerpt"]),
    )
