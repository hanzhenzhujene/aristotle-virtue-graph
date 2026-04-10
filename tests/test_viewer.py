from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from aristotle_graph.app.streamlit_app import apply_pending_view_navigation
from aristotle_graph.viewer.load import approved_empty_notice, load_viewer_dataset
from aristotle_graph.viewer.state import (
    VIEW_NAMES,
    ViewerFilters,
    build_filtered_graph,
    default_concept_id,
    graph_degree_rows,
    passage_options,
    start_here_concept_ids,
)


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

    assert len(dataset.concepts) == 42
    assert len(dataset.relations) == 33
    assert len(dataset.passages) == 45
    assert dataset.empty_notice is None


def test_default_concept_prefers_courage() -> None:
    dataset = load_viewer_dataset("candidate")

    assert default_concept_id(dataset, dataset.concepts) == "courage"


def test_start_here_concepts_include_curated_entry_points() -> None:
    dataset = load_viewer_dataset("candidate")

    assert start_here_concept_ids(dataset) == [
        "courage",
        "temperance",
        "liberality",
        "truthfulness",
        "moral-virtue",
    ]


def test_view_names_include_overall_map_before_stats() -> None:
    assert VIEW_NAMES == (
        "Concept Explorer",
        "Passage Explorer",
        "Graph View",
        "Overall Map",
        "Stats",
    )


def test_passage_options_include_focused_passage_outside_current_filter() -> None:
    dataset = load_viewer_dataset("candidate")
    visible_passages = [dataset.passages[0]]

    options = passage_options(
        dataset,
        visible_passages,
        focused_passage_id="ne.b2.s7.p4",
    )

    assert options[0].passage_id == "ne.b2.s7.p4"
    assert options[1].passage_id == visible_passages[0].passage_id


def test_build_filtered_graph_returns_consistent_node_edge_subset() -> None:
    dataset = load_viewer_dataset("candidate")
    filters = ViewerFilters(
        concept_kinds=frozenset({"virtue", "vice"}),
        relation_types=frozenset({"has_excess", "has_deficiency"}),
        assertion_tiers=frozenset({"textual"}),
        sections=frozenset({7}),
    )

    nodes, relations = build_filtered_graph(dataset, filters, include_isolates=False)
    node_ids = {concept.id for concept in nodes}

    assert nodes
    assert relations
    assert all(relation.source_id in node_ids for relation in relations)
    assert all(relation.target_id in node_ids for relation in relations)


def test_graph_degree_rows_sort_by_total_degree() -> None:
    dataset = load_viewer_dataset("candidate")
    nodes, relations = build_filtered_graph(dataset, ViewerFilters())

    rows = graph_degree_rows(nodes, relations)

    assert rows
    assert cast(int, rows[0]["total_degree"]) >= cast(int, rows[-1]["total_degree"])
    assert {"label", "id", "kind", "in_degree", "out_degree", "total_degree"} <= set(
        rows[0]
    )


def test_apply_pending_view_navigation_switches_view_on_next_rerun() -> None:
    session_state: dict[str, object] = {
        "avg-active-view": "Concept Explorer",
        "avg-pending-view": "Passage Explorer",
    }

    apply_pending_view_navigation(
        session_state,
        active_view_key="avg-active-view",
        pending_view_key="avg-pending-view",
    )

    assert session_state["avg-active-view"] == "Passage Explorer"
    assert "avg-pending-view" not in session_state


def test_apply_pending_view_navigation_recovers_invalid_active_view() -> None:
    session_state: dict[str, object] = {"avg-active-view": "Bad View"}

    apply_pending_view_navigation(
        session_state,
        active_view_key="avg-active-view",
        pending_view_key="avg-pending-view",
    )

    assert session_state["avg-active-view"] == "Concept Explorer"


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
