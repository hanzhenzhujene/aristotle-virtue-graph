from __future__ import annotations

from io import BytesIO
from typing import cast
from zipfile import ZipFile

from aristotle_graph.app.streamlit_app import (
    apply_pending_concept_selection,
    apply_pending_view_navigation,
    queue_graph_click_navigation,
)
from aristotle_graph.viewer.downloads import build_dataset_bundle
from aristotle_graph.viewer.load import load_viewer_dataset
from aristotle_graph.viewer.render import build_graph_html, concept_story_markdown
from aristotle_graph.viewer.state import (
    VIEW_NAMES,
    ViewerFilters,
    build_ego_graph,
    build_filtered_graph,
    default_concept_id,
    graph_degree_rows,
    passage_options,
    start_here_concept_ids,
)


def test_viewer_loader_succeeds_on_repository_reviewed_exports() -> None:
    dataset = load_viewer_dataset()

    assert len(dataset.concepts) == 54
    assert len(dataset.relations) == 42
    assert len(dataset.passages) == 45
    assert dataset.paths.graphml_path.exists()


def test_default_concept_prefers_courage() -> None:
    dataset = load_viewer_dataset()

    assert default_concept_id(dataset, dataset.concepts) == "courage"


def test_start_here_concepts_include_curated_entry_points() -> None:
    dataset = load_viewer_dataset()

    assert start_here_concept_ids(dataset) == [
        "courage",
        "temperance",
        "liberality",
        "truthfulness",
        "moral-virtue",
    ]


def test_view_names_embed_the_local_graph_inside_concept_explorer() -> None:
    assert VIEW_NAMES == (
        "Home",
        "Concept Explorer",
        "Passage Explorer",
        "Overall Map",
        "Stats",
    )


def test_passage_options_include_focused_passage_outside_current_filter() -> None:
    dataset = load_viewer_dataset()
    visible_passages = [dataset.passages[0]]

    options = passage_options(
        dataset,
        visible_passages,
        focused_passage_id="ne.b2.s7.p4",
    )

    assert options[0].passage_id == "ne.b2.s7.p4"
    assert options[1].passage_id == visible_passages[0].passage_id


def test_build_filtered_graph_returns_consistent_node_edge_subset() -> None:
    dataset = load_viewer_dataset()
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
    dataset = load_viewer_dataset()
    nodes, relations = build_filtered_graph(dataset, ViewerFilters())

    rows = graph_degree_rows(nodes, relations)

    assert rows
    assert cast(int, rows[0]["total_degree"]) >= cast(int, rows[-1]["total_degree"])
    assert {"label", "id", "kind", "in_degree", "out_degree", "total_degree"} <= set(
        rows[0]
    )


def test_apply_pending_view_navigation_switches_view_on_next_rerun() -> None:
    session_state: dict[str, object] = {
        "avg-active-view": "Home",
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

    assert session_state["avg-active-view"] == "Home"


def test_apply_pending_concept_selection_updates_selected_concept() -> None:
    dataset = load_viewer_dataset()
    session_state: dict[str, object] = {
        "avg-selected-concept-id": "temperance",
        "avg-pending-concept-id": "courage",
    }

    apply_pending_concept_selection(
        session_state,
        selected_concept_key="avg-selected-concept-id",
        pending_concept_key="avg-pending-concept-id",
        dataset=dataset,
    )

    assert session_state["avg-selected-concept-id"] == "courage"
    assert "avg-pending-concept-id" not in session_state


def test_queue_graph_click_navigation_queues_concept_explorer() -> None:
    dataset = load_viewer_dataset()
    session_state: dict[str, object] = {}

    changed = queue_graph_click_navigation(
        session_state,
        clicked_concept_id="courage",
        pending_concept_key="avg-pending-concept-id",
        pending_view_key="avg-pending-view",
        dataset=dataset,
    )

    assert changed is True
    assert session_state["avg-pending-concept-id"] == "courage"
    assert session_state["avg-pending-view"] == "Concept Explorer"


def test_concept_story_markdown_handles_triad_and_principle_nodes() -> None:
    dataset = load_viewer_dataset()

    courage_story = concept_story_markdown(dataset.concept_index["courage"], dataset)
    assert "mean between cowardice and rashness" in courage_story
    assert "fear and confidence" in courage_story

    mean_story = concept_story_markdown(dataset.concept_index["ethical-mean"], dataset)
    assert "determined by rational principle and the man of practical wisdom" in mean_story
    assert "contrasts the mean with deficiency and excess" in mean_story


def test_build_dataset_bundle_contains_reviewed_exports() -> None:
    dataset = load_viewer_dataset()
    bundle = build_dataset_bundle(dataset)

    with ZipFile(BytesIO(bundle.payload)) as archive:
        names = set(archive.namelist())

    assert bundle.filename.endswith(".zip")
    assert {
        "README.txt",
        "book2_passages.jsonl",
        "book2_concepts.jsonl",
        "book2_relations.jsonl",
        "book2_graph.json",
        "book2_graph.graphml",
        "book2_stats.json",
    } <= names


def test_build_graph_html_includes_click_bridge() -> None:
    dataset = load_viewer_dataset()
    nodes, relations = build_ego_graph(dataset, "courage", ViewerFilters(), hops=1)

    html = build_graph_html(nodes, relations, center_concept_id="courage")

    assert "avg-node-click" in html
