from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from aristotle_graph.annotations.models import ConceptAnnotation, RelationAnnotation
from aristotle_graph.config import get_settings
from aristotle_graph.schemas import PassageRecord
from aristotle_graph.utils.io import read_json, read_jsonl

ReviewMode = Literal["candidate", "approved"]


class ViewerDataError(RuntimeError):
    """Raised when the processed viewer dataset cannot be loaded."""


@dataclass(frozen=True)
class ViewerPaths:
    base_dir: Path
    concepts_path: Path
    relations_path: Path
    passages_path: Path
    graph_path: Path
    stats_path: Path


@dataclass(frozen=True)
class ViewerDataset:
    mode: ReviewMode
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
    empty_notice: str | None = None


def mode_base_dir(mode: ReviewMode, *, processed_root: Path | None = None) -> Path:
    base_root = processed_root or get_settings().processed_dir
    return base_root if mode == "candidate" else base_root / "approved"


def viewer_paths(mode: ReviewMode, *, processed_root: Path | None = None) -> ViewerPaths:
    base_dir = mode_base_dir(mode, processed_root=processed_root)
    return ViewerPaths(
        base_dir=base_dir,
        concepts_path=base_dir / "book2_concepts.jsonl",
        relations_path=base_dir / "book2_relations.jsonl",
        passages_path=base_dir / "book2_passages.jsonl",
        graph_path=base_dir / "book2_graph.json",
        stats_path=base_dir / "book2_stats.json",
    )


def approved_empty_notice() -> str:
    return (
        "No reviewed subset is available yet in approved mode. Promote reviewed items from "
        "`annotations/book2/*.candidate.yaml` into the matching `*.approved.yaml` files, then "
        "run the strict export path. See `annotations/book2/README.md` and "
        "`docs/annotation_guide.md`."
    )


def _missing_artifact_message(mode: ReviewMode, missing_paths: list[Path]) -> str:
    command = (
        "python -m aristotle_graph.cli annotations export-all"
        if mode == "candidate"
        else "python -m aristotle_graph.cli annotations export-all --strict-approved "
        "--output-dir data/processed/approved"
    )
    missing_text = "\n".join(f"- {path}" for path in missing_paths)
    return (
        "Missing processed viewer artifacts:\n"
        f"{missing_text}\n"
        f"Build them with:\n{command}"
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
    mode: ReviewMode = "candidate",
    *,
    processed_root: Path | None = None,
) -> ViewerDataset:
    paths = viewer_paths(mode, processed_root=processed_root)
    required_paths = [
        paths.concepts_path,
        paths.relations_path,
        paths.passages_path,
        paths.graph_path,
    ]
    missing = [path for path in required_paths if not path.exists()]
    if missing:
        raise ViewerDataError(_missing_artifact_message(mode, missing))

    concepts = tuple(
        sorted(
            (
                ConceptAnnotation.model_validate(row)
                for row in read_jsonl(paths.concepts_path)
            ),
            key=lambda concept: concept.primary_label.lower(),
        )
    )
    relations = tuple(
        sorted(
            (
                RelationAnnotation.model_validate(row)
                for row in read_jsonl(paths.relations_path)
            ),
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
    stats = read_json(paths.stats_path) if paths.stats_path.exists() else {
        "book": 2,
        "mode": mode,
        "concept_count": len(concepts),
        "relation_count": len(relations),
        "passage_count": len(passages),
    }

    empty_notice = None
    if mode == "approved" and not concepts and not relations:
        empty_notice = approved_empty_notice()

    return ViewerDataset(
        mode=mode,
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
        empty_notice=empty_notice,
    )
