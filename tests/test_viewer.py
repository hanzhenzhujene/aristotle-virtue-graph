from __future__ import annotations

import json
from pathlib import Path

from aristotle_graph.viewer.load import approved_empty_notice, load_viewer_dataset
from aristotle_graph.viewer.state import default_concept_id


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_viewer_loader_succeeds_on_repository_candidate_exports() -> None:
    dataset = load_viewer_dataset("candidate")

    assert len(dataset.concepts) == 54
    assert len(dataset.relations) == 42
    assert len(dataset.passages) == 45
    assert dataset.empty_notice is None


def test_viewer_loader_succeeds_on_repository_approved_exports() -> None:
    dataset = load_viewer_dataset("approved")

    assert len(dataset.concepts) == 26
    assert len(dataset.relations) == 21
    assert len(dataset.passages) == 45
    assert dataset.empty_notice is None


def test_default_concept_prefers_courage() -> None:
    dataset = load_viewer_dataset("candidate")

    assert default_concept_id(dataset, dataset.concepts) == "courage"


def test_viewer_loader_handles_empty_approved_mode(tmp_path: Path) -> None:
    approved_root = tmp_path / "approved"
    _write_jsonl(approved_root / "book2_concepts.jsonl", [])
    _write_jsonl(approved_root / "book2_relations.jsonl", [])
    _write_jsonl(
        approved_root / "book2_passages.jsonl",
        [
            {
                "passage_id": "ne.b2.s1.p1",
                "work_id": "nicomachean-ethics",
                "book_number": 2,
                "chapter_or_section": "part-1",
                "sequence_in_book": 1,
                "source_id": "wikisource_ross_1908",
                "source_url": "https://example.test/book-two#Part_1",
                "citation_label": "NE II.1 ¶1",
                "text": "Fixture passage text.",
                "cts_urn": None,
                "bekker_ref": None,
                "char_count": 21,
                "hash": "fixture-hash",
            }
        ],
    )
    (approved_root / "book2_graph.json").write_text(
        json.dumps(
            {
                "meta": {
                    "book": 2,
                    "mode": "strict_approved",
                    "concept_count": 0,
                    "relation_count": 0,
                    "passage_count": 1,
                },
                "nodes": [],
                "edges": [],
                "passages": [],
            }
        ),
        encoding="utf-8",
    )
    (approved_root / "book2_stats.json").write_text(
        json.dumps(
            {
                "book": 2,
                "mode": "strict_approved",
                "concept_count": 0,
                "relation_count": 0,
                "passage_count": 1,
            }
        ),
        encoding="utf-8",
    )

    dataset = load_viewer_dataset("approved", processed_root=tmp_path)

    assert dataset.empty_notice == approved_empty_notice()
    assert len(dataset.concepts) == 0
    assert len(dataset.relations) == 0
    assert len(dataset.passages) == 1
