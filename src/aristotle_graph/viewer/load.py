from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aristotle_graph.annotations.models import ConceptAnnotation, RelationAnnotation
from aristotle_graph.config import get_settings
from aristotle_graph.schemas import PassageRecord
from aristotle_graph.utils.io import read_json, read_jsonl


class ViewerDataError(RuntimeError):
    """Raised when the processed viewer dataset cannot be loaded."""


@dataclass(frozen=True)
class ViewerPaths:
    base_dir: Path
    concepts_path: Path
    relations_path: Path
    passages_path: Path
    graph_path: Path
    graphml_path: Path
    stats_path: Path


@dataclass(frozen=True)
class ViewerDataset:
    paths: ViewerPaths
    concepts: tuple[ConceptAnnotation, ...]
    relations: tuple[RelationAnnotation, ...]
    passages: tuple[PassageRecord, ...]
    graph_payload: dict[str, Any]
    stats: dict[str, Any]
    concept_index: dict[str, ConceptAnnotation]
    passage_index: dict[str, PassageRecord]
    outgoing_relations: dict[str, tuple[RelationAnnotation, ...]]
    incoming_relations: dict[str, tuple[RelationAnnotation, ...]]
    concepts_by_passage: dict[str, tuple[ConceptAnnotation, ...]]
    relations_by_passage: dict[str, tuple[RelationAnnotation, ...]]


def viewer_paths(*, processed_root: Path | None = None) -> ViewerPaths:
    base_dir = processed_root or get_settings().processed_dir
    return ViewerPaths(
        base_dir=base_dir,
        concepts_path=base_dir / "book2_concepts.jsonl",
        relations_path=base_dir / "book2_relations.jsonl",
        passages_path=base_dir / "book2_passages.jsonl",
        graph_path=base_dir / "book2_graph.json",
        graphml_path=base_dir / "book2_graph.graphml",
        stats_path=base_dir / "book2_stats.json",
    )


def _missing_artifact_message(missing_paths: list[Path]) -> str:
    missing_text = "\n".join(f"- {path}" for path in missing_paths)
    return (
        "Missing processed viewer artifacts:\n"
        f"{missing_text}\n"
        "Build the reviewed Book II dataset with:\n"
        "make annotations-export"
    )


def _sorted_relation_index(
    relations: tuple[RelationAnnotation, ...],
    *,
    key_func: Any,
) -> dict[str, tuple[RelationAnnotation, ...]]:
    index: dict[str, list[RelationAnnotation]] = {}
    for relation in relations:
        key = key_func(relation)
        index.setdefault(key, []).append(relation)
    return {
        key: tuple(sorted(value, key=lambda relation: relation.id))
        for key, value in index.items()
    }


def _concepts_by_passage(
    concepts: tuple[ConceptAnnotation, ...],
) -> dict[str, tuple[ConceptAnnotation, ...]]:
    index: dict[str, list[ConceptAnnotation]] = {}
    for concept in concepts:
        for evidence in concept.evidence:
            index.setdefault(evidence.passage_id, []).append(concept)
    return {
        key: tuple(sorted(value, key=lambda concept: concept.primary_label.lower()))
        for key, value in index.items()
    }


def _relations_by_passage(
    relations: tuple[RelationAnnotation, ...],
) -> dict[str, tuple[RelationAnnotation, ...]]:
    index: dict[str, list[RelationAnnotation]] = {}
    for relation in relations:
        for evidence in relation.evidence:
            index.setdefault(evidence.passage_id, []).append(relation)
    return {
        key: tuple(sorted(value, key=lambda relation: relation.id))
        for key, value in index.items()
    }


def load_viewer_dataset(
    *,
    processed_root: Path | None = None,
) -> ViewerDataset:
    paths = viewer_paths(processed_root=processed_root)
    required_paths = [
        paths.concepts_path,
        paths.relations_path,
        paths.passages_path,
        paths.graph_path,
        paths.graphml_path,
        paths.stats_path,
    ]
    missing = [path for path in required_paths if not path.exists()]
    if missing:
        raise ViewerDataError(_missing_artifact_message(missing))

    concepts = tuple(
        sorted(
            (ConceptAnnotation.model_validate(row) for row in read_jsonl(paths.concepts_path)),
            key=lambda concept: concept.primary_label.lower(),
        )
    )
    relations = tuple(
        sorted(
            (RelationAnnotation.model_validate(row) for row in read_jsonl(paths.relations_path)),
            key=lambda relation: relation.id,
        )
    )
    passages = tuple(
        sorted(
            (PassageRecord.model_validate(row) for row in read_jsonl(paths.passages_path)),
            key=lambda passage: passage.sequence_in_book,
        )
    )

    graph_payload = read_json(paths.graph_path)
    stats = read_json(paths.stats_path)

    return ViewerDataset(
        paths=paths,
        concepts=concepts,
        relations=relations,
        passages=passages,
        graph_payload=graph_payload,
        stats=stats,
        concept_index={concept.id: concept for concept in concepts},
        passage_index={passage.passage_id: passage for passage in passages},
        outgoing_relations=_sorted_relation_index(
            relations,
            key_func=lambda relation: relation.source_id,
        ),
        incoming_relations=_sorted_relation_index(
            relations,
            key_func=lambda relation: relation.target_id,
        ),
        concepts_by_passage=_concepts_by_passage(concepts),
        relations_by_passage=_relations_by_passage(relations),
    )
