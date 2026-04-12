from __future__ import annotations

import re
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
    book_number: int
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


_BOOK_PATH_RE = re.compile(r"^book(?P<book>\d+)_concepts\.jsonl$")


def viewer_paths(*, book: int = 2, processed_root: Path | None = None) -> ViewerPaths:
    base_dir = processed_root or get_settings().processed_dir
    return ViewerPaths(
        base_dir=base_dir,
        concepts_path=base_dir / f"book{book}_concepts.jsonl",
        relations_path=base_dir / f"book{book}_relations.jsonl",
        passages_path=base_dir / f"book{book}_passages.jsonl",
        graph_path=base_dir / f"book{book}_graph.json",
        graphml_path=base_dir / f"book{book}_graph.graphml",
        stats_path=base_dir / f"book{book}_stats.json",
    )


def available_viewer_books(*, processed_root: Path | None = None) -> list[int]:
    base_dir = processed_root or get_settings().processed_dir
    books: list[int] = []
    for path in sorted(base_dir.glob("book*_concepts.jsonl")):
        match = _BOOK_PATH_RE.fullmatch(path.name)
        if match is None:
            continue
        book = int(match.group("book"))
        paths = viewer_paths(book=book, processed_root=base_dir)
        required_paths = (
            paths.concepts_path,
            paths.relations_path,
            paths.passages_path,
            paths.graph_path,
            paths.graphml_path,
            paths.stats_path,
        )
        if all(required_path.exists() for required_path in required_paths):
            books.append(book)
    return books


def _missing_artifact_message(missing_paths: list[Path], *, book: int) -> str:
    missing_text = "\n".join(f"- {path}" for path in missing_paths)
    return (
        "Missing processed viewer artifacts:\n"
        f"{missing_text}\n"
        f"Build the processed Book {book} dataset with:\n"
        f"python -m aristotle_graph.cli annotations export-all --book {book} --strict-approved"
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
    book: int = 2,
    processed_root: Path | None = None,
) -> ViewerDataset:
    paths = viewer_paths(book=book, processed_root=processed_root)
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
        raise ViewerDataError(_missing_artifact_message(missing, book=book))

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
    passage_books = {passage.book_number for passage in passages}
    concept_books = {concept.book for concept in concepts}
    graph_book = graph_payload.get("meta", {}).get("book")
    stats_book = stats.get("book")

    if passage_books != {book}:
        msg = f"Processed passage export is not consistently Book {book}: {sorted(passage_books)}"
        raise ViewerDataError(msg)
    if concept_books != {book}:
        msg = f"Processed concept export is not consistently Book {book}: {sorted(concept_books)}"
        raise ViewerDataError(msg)
    if graph_book != book:
        msg = f"Graph payload metadata says book={graph_book}, expected {book}"
        raise ViewerDataError(msg)
    if stats_book != book:
        msg = f"Stats payload says book={stats_book}, expected {book}"
        raise ViewerDataError(msg)

    return ViewerDataset(
        book_number=book,
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
