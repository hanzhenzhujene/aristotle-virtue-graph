from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import Draft202012Validator

from aristotle_graph.annotations.models import (
    ConceptAnnotation,
    RelationAnnotation,
    ReviewStatus,
)
from aristotle_graph.config import get_settings
from aristotle_graph.schemas import PassageRecord
from aristotle_graph.utils.io import read_json, read_jsonl


class AnnotationLoadError(ValueError):
    """Raised when annotation files fail to load or schema-validate."""


@dataclass(frozen=True)
class AnnotationBundle:
    concepts: tuple[ConceptAnnotation, ...]
    relations: tuple[RelationAnnotation, ...]
    concept_files: tuple[Path, ...]
    relation_files: tuple[Path, ...]


def annotation_root(book: int = 2, *, root: Path | None = None) -> Path:
    return root or get_settings().annotations_dir / f"book{book}"


def concept_paths(book: int = 2, *, root: Path | None = None) -> tuple[Path, ...]:
    book_root = annotation_root(book, root=root)
    return (
        book_root / "concepts.candidate.yaml",
        book_root / "concepts.approved.yaml",
    )


def relation_paths(book: int = 2, *, root: Path | None = None) -> tuple[Path, ...]:
    book_root = annotation_root(book, root=root)
    return (
        book_root / "relations.candidate.yaml",
        book_root / "relations.approved.yaml",
    )


def passage_authority_path(book: int = 2, *, path: Path | None = None) -> Path:
    return path or get_settings().interim_dir / f"book{book}_passages.jsonl"


def load_passage_authority(book: int = 2, *, path: Path | None = None) -> tuple[PassageRecord, ...]:
    rows = read_jsonl(passage_authority_path(book, path=path))
    return tuple(PassageRecord.model_validate(row) for row in rows)


@cache
def load_json_schema(schema_name: str) -> dict[str, Any]:
    schema_path = get_settings().schema_dir / schema_name
    return cast(dict[str, Any], read_json(schema_path))


def _expected_status_from_path(path: Path) -> ReviewStatus:
    if ".candidate." in path.name:
        return "candidate"
    if ".approved." in path.name:
        return "approved"
    msg = f"Could not infer review status from annotation filename: {path.name}"
    raise AnnotationLoadError(msg)


def _load_yaml_sequence(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        msg = f"Missing annotation file: {path}"
        raise AnnotationLoadError(msg)

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload is None:
        return []
    if not isinstance(payload, list):
        msg = f"Annotation file must contain a top-level YAML list: {path}"
        raise AnnotationLoadError(msg)
    if not all(isinstance(item, dict) for item in payload):
        msg = f"Every annotation entry must be a mapping: {path}"
        raise AnnotationLoadError(msg)
    return payload


def _schema_errors(schema_name: str, item: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(load_json_schema(schema_name))
    errors = sorted(validator.iter_errors(item), key=lambda error: list(error.path))
    return [error.message for error in errors]


def _load_concepts_from_path(path: Path) -> list[ConceptAnnotation]:
    expected_status = _expected_status_from_path(path)
    raw_items = _load_yaml_sequence(path)
    concepts: list[ConceptAnnotation] = []
    for index, item in enumerate(raw_items, start=1):
        schema_errors = _schema_errors("concept.schema.json", item)
        if schema_errors:
            joined = "; ".join(schema_errors)
            msg = f"{path}:{index}: concept schema validation failed: {joined}"
            raise AnnotationLoadError(msg)
        concept = ConceptAnnotation.model_validate(item)
        if concept.review_status != expected_status:
            msg = (
                f"{path}:{index}: concept review_status={concept.review_status} does not match "
                f"the file status {expected_status}"
            )
            raise AnnotationLoadError(msg)
        concepts.append(concept)
    return concepts


def _load_relations_from_path(path: Path) -> list[RelationAnnotation]:
    expected_status = _expected_status_from_path(path)
    raw_items = _load_yaml_sequence(path)
    relations: list[RelationAnnotation] = []
    for index, item in enumerate(raw_items, start=1):
        schema_errors = _schema_errors("relation.schema.json", item)
        if schema_errors:
            joined = "; ".join(schema_errors)
            msg = f"{path}:{index}: relation schema validation failed: {joined}"
            raise AnnotationLoadError(msg)
        relation = RelationAnnotation.model_validate(item)
        if relation.review_status != expected_status:
            msg = (
                f"{path}:{index}: relation review_status={relation.review_status} does not match "
                f"the file status {expected_status}"
            )
            raise AnnotationLoadError(msg)
        relations.append(relation)
    return relations


def load_annotation_bundle(book: int = 2, *, root: Path | None = None) -> AnnotationBundle:
    concept_file_paths = concept_paths(book, root=root)
    relation_file_paths = relation_paths(book, root=root)

    concepts = tuple(
        concept
        for path in concept_file_paths
        for concept in _load_concepts_from_path(path)
    )
    relations = tuple(
        relation
        for path in relation_file_paths
        for relation in _load_relations_from_path(path)
    )

    return AnnotationBundle(
        concepts=concepts,
        relations=relations,
        concept_files=concept_file_paths,
        relation_files=relation_file_paths,
    )
