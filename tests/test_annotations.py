from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx
import pytest
import yaml

from aristotle_graph.annotations.export import export_all
from aristotle_graph.annotations.load import (
    AnnotationLoadError,
    load_annotation_bundle,
    load_passage_authority,
)
from aristotle_graph.annotations.validate import (
    AnnotationValidationError,
    validate_annotation_bundle,
)


def _write_yaml(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(rows, sort_keys=False), encoding="utf-8")


def _make_passage(passage_id: str, sequence_in_book: int) -> dict[str, Any]:
    _, _, section_part, paragraph_part = passage_id.split(".")
    section_number = int(section_part.removeprefix("s"))
    paragraph_number = int(paragraph_part.removeprefix("p"))
    return {
        "passage_id": passage_id,
        "work_id": "nicomachean-ethics",
        "book_number": 2,
        "chapter_or_section": f"part-{section_number}",
        "sequence_in_book": sequence_in_book,
        "source_id": "wikisource_ross_1908",
        "source_url": f"https://example.test/book-two#Part_{section_number}",
        "citation_label": f"NE II.{section_number} ¶{paragraph_number}",
        "text": f"Fixture text for {passage_id}.",
        "cts_urn": None,
        "bekker_ref": None,
        "char_count": 24,
        "hash": f"hash-{passage_id}",
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _write_annotation_fixture(
    tmp_path: Path,
    *,
    concepts_candidate: list[dict[str, Any]],
    relations_candidate: list[dict[str, Any]],
    concepts_approved: list[dict[str, Any]] | None = None,
    relations_approved: list[dict[str, Any]] | None = None,
    passage_ids: list[str] | None = None,
) -> tuple[Path, Path]:
    annotation_root = tmp_path / "annotations" / "book2"
    _write_yaml(annotation_root / "concepts.candidate.yaml", concepts_candidate)
    _write_yaml(annotation_root / "concepts.approved.yaml", concepts_approved or [])
    _write_yaml(annotation_root / "relations.candidate.yaml", relations_candidate)
    _write_yaml(annotation_root / "relations.approved.yaml", relations_approved or [])

    passage_path = tmp_path / "book2_passages.jsonl"
    rows = [
        _make_passage(passage_id, sequence)
        for sequence, passage_id in enumerate(passage_ids or ["ne.b2.s1.p1"], start=1)
    ]
    _write_jsonl(passage_path, rows)
    return annotation_root, passage_path


def _concept(
    *,
    concept_id: str,
    passage_id: str = "ne.b2.s1.p1",
    review_status: str = "candidate",
) -> dict[str, Any]:
    return {
        "id": concept_id,
        "primary_label": concept_id.replace("-", " "),
        "source_labels": [concept_id.replace("-", " ")],
        "kind": "principle",
        "description": f"Description for {concept_id}.",
        "assertion_tier": "textual",
        "book": 2,
        "sections": [1],
        "evidence": [
            {
                "passage_id": passage_id,
                "support_type": "direct",
                "note": f"Evidence for {concept_id}.",
            }
        ],
        "review_status": review_status,
    }


def _relation(
    *,
    relation_id: str,
    source_id: str,
    relation_type: str,
    target_id: str,
    passage_id: str = "ne.b2.s1.p1",
    review_status: str = "candidate",
) -> dict[str, Any]:
    return {
        "id": relation_id,
        "source_id": source_id,
        "relation_type": relation_type,
        "target_id": target_id,
        "assertion_tier": "textual",
        "evidence": [
            {
                "passage_id": passage_id,
                "support_type": "direct",
                "note": f"Evidence for {relation_id}.",
            }
        ],
        "review_status": review_status,
    }


def test_schema_validation_rejects_missing_required_field(tmp_path: Path) -> None:
    bad_concept = _concept(concept_id="habit")
    del bad_concept["primary_label"]
    annotation_root, _ = _write_annotation_fixture(
        tmp_path,
        concepts_candidate=[bad_concept],
        relations_candidate=[],
    )

    with pytest.raises(AnnotationLoadError):
        load_annotation_bundle(root=annotation_root)


def test_duplicate_id_rejection(tmp_path: Path) -> None:
    annotation_root, passage_path = _write_annotation_fixture(
        tmp_path,
        concepts_candidate=[_concept(concept_id="habit"), _concept(concept_id="habit")],
        relations_candidate=[],
    )

    bundle = load_annotation_bundle(root=annotation_root)
    passages = load_passage_authority(path=passage_path)

    with pytest.raises(AnnotationValidationError, match="duplicate concept id: habit"):
        validate_annotation_bundle(bundle, passages)


def test_missing_passage_rejection(tmp_path: Path) -> None:
    annotation_root, passage_path = _write_annotation_fixture(
        tmp_path,
        concepts_candidate=[_concept(concept_id="habit", passage_id="ne.b2.s1.p2")],
        relations_candidate=[],
        passage_ids=["ne.b2.s1.p1"],
    )

    bundle = load_annotation_bundle(root=annotation_root)
    passages = load_passage_authority(path=passage_path)

    with pytest.raises(
        AnnotationValidationError,
        match="concept habit references missing passage ne.b2.s1.p2",
    ):
        validate_annotation_bundle(bundle, passages)


def test_missing_concept_reference_rejection(tmp_path: Path) -> None:
    annotation_root, passage_path = _write_annotation_fixture(
        tmp_path,
        concepts_candidate=[_concept(concept_id="habit")],
        relations_candidate=[
            _relation(
                relation_id="habit--formed-by--training",
                source_id="habit",
                relation_type="formed_by",
                target_id="training",
            )
        ],
    )

    bundle = load_annotation_bundle(root=annotation_root)
    passages = load_passage_authority(path=passage_path)

    with pytest.raises(
        AnnotationValidationError,
        match="relation habit--formed-by--training references missing target concept training",
    ):
        validate_annotation_bundle(bundle, passages)


def test_strict_mode_rejects_candidate_only_dependency(tmp_path: Path) -> None:
    annotation_root, passage_path = _write_annotation_fixture(
        tmp_path,
        concepts_candidate=[_concept(concept_id="habit", review_status="candidate")],
        relations_candidate=[],
        concepts_approved=[_concept(concept_id="virtue", review_status="approved")],
        relations_approved=[
            _relation(
                relation_id="virtue--formed-by--habit",
                source_id="virtue",
                relation_type="formed_by",
                target_id="habit",
                review_status="approved",
            )
        ],
    )

    bundle = load_annotation_bundle(root=annotation_root)
    passages = load_passage_authority(path=passage_path)

    with pytest.raises(
        AnnotationValidationError,
        match="approved relation virtue--formed-by--habit must only reference approved concepts",
    ):
        validate_annotation_bundle(bundle, passages, strict_approved=True)


def test_processed_export_succeeds_for_repository_candidate_seed(tmp_path: Path) -> None:
    bundle = load_annotation_bundle()
    passages = load_passage_authority()
    validated = validate_annotation_bundle(bundle, passages)

    paths = export_all(validated, output_dir=tmp_path)

    assert paths.concepts_path.exists()
    assert paths.relations_path.exists()
    assert paths.graph_path.exists()
    assert paths.graphml_path.exists()
    assert paths.passages_path.exists()
    assert paths.stats_path.exists()

    graph = json.loads(paths.graph_path.read_text(encoding="utf-8"))
    stats = json.loads(paths.stats_path.read_text(encoding="utf-8"))
    graphml = nx.read_graphml(paths.graphml_path)
    passages = [
        json.loads(line)
        for line in paths.passages_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert graph["meta"]["mode"] == "candidate"
    assert len(graph["nodes"]) == 54
    assert len(graph["edges"]) == 42
    assert len(graph["passages"]) == 45
    assert stats["concept_count"] == 54
    assert stats["relation_count"] == 42
    assert stats["passage_count"] == 45
    assert len(passages) == 45
    assert graphml.number_of_nodes() == 54
    assert graphml.number_of_edges() == 42


def test_processed_export_succeeds_for_repository_approved_seed(tmp_path: Path) -> None:
    bundle = load_annotation_bundle()
    passages = load_passage_authority()
    validated = validate_annotation_bundle(bundle, passages, strict_approved=True)

    paths = export_all(validated, output_dir=tmp_path)

    graph = json.loads(paths.graph_path.read_text(encoding="utf-8"))
    stats = json.loads(paths.stats_path.read_text(encoding="utf-8"))
    graphml = nx.read_graphml(paths.graphml_path)
    approved_passages = [
        json.loads(line)
        for line in paths.passages_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert graph["meta"]["mode"] == "strict_approved"
    assert len(graph["nodes"]) == 34
    assert len(graph["edges"]) == 27
    assert len(graph["passages"]) == 45
    assert stats["concept_count"] == 34
    assert stats["relation_count"] == 27
    assert stats["passage_count"] == 45
    assert stats["concept_review_statuses"] == {"approved": 34}
    assert stats["relation_review_statuses"] == {"approved": 27}
    assert len(approved_passages) == 45
    assert graphml.number_of_nodes() == 34
    assert graphml.number_of_edges() == 27
