from __future__ import annotations

import importlib
from collections import Counter
from collections.abc import Callable, MutableMapping
from pathlib import Path
from typing import Any, cast

from aristotle_graph.annotations.models import ConceptAnnotation, RelationAnnotation
from aristotle_graph.schemas import PassageRecord
from aristotle_graph.viewer.downloads import DownloadArtifact, build_download_artifacts
from aristotle_graph.viewer.graph_component import render_clickable_graph
from aristotle_graph.viewer.load import ViewerDataError, ViewerDataset, load_viewer_dataset
from aristotle_graph.viewer.render import (
    build_graph_html,
    concept_detail_rows,
    concept_story_markdown,
    concept_summary_rows,
    evidence_rows,
    intro_markdown,
    kind_legend_html,
    passage_preview,
    passage_relation_rows,
    relation_rows,
)
from aristotle_graph.viewer.state import (
    VIEW_NAMES,
    ViewerFilters,
    available_assertion_tiers,
    available_concept_kinds,
    available_relation_types,
    build_ego_graph,
    build_filtered_graph,
    concept_stats,
    default_concept_id,
    evidence_passage_ids,
    filter_concepts,
    filter_passages,
    filter_relations,
    graph_degree_rows,
    home_concept_ids,
    home_passage_id,
    passage_options,
    relation_sort_key,
    relation_stats,
    start_here_concept_ids,
)

HOME_VIEW, CONCEPT_VIEW, PASSAGE_VIEW, OVERALL_MAP_VIEW, STATS_VIEW = VIEW_NAMES


def apply_pending_view_navigation(
    session_state: MutableMapping[str, object],
    *,
    active_view_key: str,
    pending_view_key: str,
) -> None:
    pending_view = session_state.pop(pending_view_key, None)
    if pending_view in VIEW_NAMES:
        session_state[active_view_key] = pending_view
        return
    if session_state.get(active_view_key) not in VIEW_NAMES:
        session_state[active_view_key] = HOME_VIEW


def apply_pending_concept_selection(
    session_state: MutableMapping[str, object],
    *,
    selected_concept_key: str,
    pending_concept_key: str,
    dataset: ViewerDataset,
) -> None:
    pending_concept_id = session_state.pop(pending_concept_key, None)
    if isinstance(pending_concept_id, str) and pending_concept_id in dataset.concept_index:
        session_state[selected_concept_key] = pending_concept_id


def apply_pending_passage_selection(
    session_state: MutableMapping[str, object],
    *,
    selected_passage_key: str,
    pending_passage_key: str,
    dataset: ViewerDataset,
) -> None:
    pending_passage_id = session_state.pop(pending_passage_key, None)
    if isinstance(pending_passage_id, str) and pending_passage_id in dataset.passage_index:
        session_state[selected_passage_key] = pending_passage_id


def queue_concept_navigation(
    session_state: MutableMapping[str, object],
    *,
    concept_id: str,
    pending_concept_key: str,
    pending_view_key: str,
) -> None:
    session_state[pending_concept_key] = concept_id
    session_state[pending_view_key] = CONCEPT_VIEW


def queue_passage_navigation(
    session_state: MutableMapping[str, object],
    *,
    passage_id: str,
    pending_passage_key: str,
    pending_view_key: str,
) -> None:
    session_state[pending_passage_key] = passage_id
    session_state[pending_view_key] = PASSAGE_VIEW


def queue_graph_click_navigation(
    session_state: MutableMapping[str, object],
    *,
    clicked_concept_id: str | None,
    pending_concept_key: str,
    pending_view_key: str,
    dataset: ViewerDataset,
) -> bool:
    if clicked_concept_id is None or clicked_concept_id not in dataset.concept_index:
        return False
    queue_concept_navigation(
        session_state,
        concept_id=clicked_concept_id,
        pending_concept_key=pending_concept_key,
        pending_view_key=pending_view_key,
    )
    return True


def _relation_label(relation_type: str) -> str:
    return relation_type.replace("_", " ")


def _relation_caption(relation: RelationAnnotation, dataset: ViewerDataset) -> str:
    passage_ids = evidence_passage_ids(relation.evidence)
    if not passage_ids:
        return relation.assertion_tier.replace("_", " ")
    passage = dataset.passage_index[passage_ids[0]]
    return f"{passage.citation_label} · {relation.assertion_tier.replace('_', ' ')}"


def _render_relation_cards(
    st: Any,
    *,
    title: str,
    relations: list[RelationAnnotation],
    dataset: ViewerDataset,
    selected_concept: ConceptAnnotation,
    key_prefix: str,
    queue_concept: Callable[[str], None],
    queue_passage: Callable[[str], None],
) -> None:
    st.markdown(f"#### {title}")
    if not relations:
        st.caption("No linked relations under the current filters.")
        return

    for relation in relations:
        is_outgoing = relation.source_id == selected_concept.id
        other_concept_id = relation.target_id if is_outgoing else relation.source_id
        other_concept = dataset.concept_index[other_concept_id]
        headline = (
            f"{_relation_label(relation.relation_type)} {other_concept.primary_label}"
            if is_outgoing
            else f"{other_concept.primary_label} {_relation_label(relation.relation_type)}"
        )
        passage_ids = evidence_passage_ids(relation.evidence)
        with st.container(border=True):
            st.markdown(f"**{headline}**")
            st.caption(_relation_caption(relation, dataset))
            action_left, action_right = st.columns(2)
            action_left.button(
                "Open concept",
                key=f"{key_prefix}-concept-{relation.id}",
                use_container_width=True,
                on_click=queue_concept,
                args=(other_concept_id,),
            )
            if passage_ids:
                action_right.button(
                    "Read passage",
                    key=f"{key_prefix}-passage-{relation.id}",
                    use_container_width=True,
                    on_click=queue_passage,
                    args=(passage_ids[0],),
                )


def _render_evidence_cards(
    st: Any,
    *,
    concept: ConceptAnnotation,
    dataset: ViewerDataset,
    key_prefix: str,
    queue_passage: Callable[[str], None],
) -> None:
    st.markdown("#### Read supporting passages")
    if not concept.evidence:
        st.caption("No supporting passages.")
        return

    for evidence in concept.evidence:
        passage = dataset.passage_index[evidence.passage_id]
        with st.container(border=True):
            st.markdown(f"**{passage.citation_label}**")
            st.write(passage_preview(passage.text))
            st.caption(evidence.note)
            st.button(
                "Read passage",
                key=f"{key_prefix}-{evidence.passage_id}",
                use_container_width=True,
                on_click=queue_passage,
                args=(evidence.passage_id,),
            )


def _render_passage_concept_cards(
    st: Any,
    *,
    concepts: tuple[ConceptAnnotation, ...],
    key_prefix: str,
    queue_concept: Callable[[str], None],
) -> None:
    if not concepts:
        st.caption("No linked concepts in the current dataset.")
        return

    for concept in concepts:
        with st.container(border=True):
            st.markdown(f"**{concept.primary_label}**")
            st.caption(concept.description)
            st.button(
                "Open concept",
                key=f"{key_prefix}-{concept.id}",
                use_container_width=True,
                on_click=queue_concept,
                args=(concept.id,),
            )


def _render_download_chooser(
    st: Any,
    *,
    artifacts: tuple[DownloadArtifact, ...],
    key_prefix: str,
) -> None:
    artifact_index = {artifact.key: artifact for artifact in artifacts}
    first_artifact = artifacts[0]
    with st.popover("Download dataset"):
        st.caption("Choose a file to download.")
        selected_key = cast(
            str,
            st.selectbox(
                "File",
                options=[artifact.key for artifact in artifacts],
                index=0,
                format_func=lambda artifact_key: artifact_index[artifact_key].label,
                key=f"{key_prefix}-artifact",
                label_visibility="collapsed",
            ),
        )
        selected_artifact = artifact_index.get(selected_key, first_artifact)
        st.caption(selected_artifact.description)
        st.download_button(
            f"Download {selected_artifact.label}",
            data=selected_artifact.payload,
            file_name=selected_artifact.filename,
            mime=selected_artifact.mime,
            use_container_width=True,
            key=f"{key_prefix}-download-{selected_artifact.key}",
        )


def _render_home_view(
    st: Any,
    *,
    dataset: ViewerDataset,
    download_artifacts: tuple[DownloadArtifact, ...],
    queue_concept: Callable[[str], None],
    queue_passage: Callable[[str], None],
) -> None:
    st.subheader("Start here")
    st.write(
        "Use this dashboard to move between Aristotle's conceptual structure in Book II "
        "and the exact passages that ground it."
    )

    entry_left, entry_mid, entry_right = st.columns(3)
    entry_concepts = home_concept_ids(dataset)
    first_concept = entry_concepts[0] if entry_concepts else None
    second_concept = entry_concepts[1] if len(entry_concepts) > 1 else None
    focus_passage_id = home_passage_id(dataset)

    if first_concept is not None:
        with entry_left.container(border=True):
            st.markdown("### Courage")
            st.write(
                "See Aristotle's classic triad structure: the mean, its excess, "
                "its deficiency, and the domain it concerns."
            )
            st.button(
                "Open courage",
                key="home-courage",
                use_container_width=True,
                on_click=queue_concept,
                args=(first_concept,),
            )

    if second_concept is not None:
        with entry_mid.container(border=True):
            st.markdown("### Moral virtue")
            st.write(
                "Start from formation: how Book II distinguishes moral virtue, "
                "connects it to habit, and ties it to pleasure and pain."
            )
            st.button(
                "Open moral virtue",
                key="home-moral-virtue",
                use_container_width=True,
                on_click=queue_concept,
                args=(second_concept,),
            )

    if focus_passage_id is not None:
        passage = dataset.passage_index[focus_passage_id]
        with entry_right.container(border=True):
            st.markdown("### Start from the text")
            st.write(
                "Open a dense section-7 passage first, then move outward into the linked "
                "concepts and relations."
            )
            st.caption(f"{passage.citation_label} · {passage_preview(passage.text, limit=120)}")
            st.button(
                "Read the passage",
                key="home-passage",
                use_container_width=True,
                on_click=queue_passage,
                args=(focus_passage_id,),
            )

    what_left, what_right = st.columns([1.15, 0.85])
    with what_left:
        st.markdown("### What you can do here")
        st.markdown(
            "\n".join(
                [
                    "- Trace a virtue, vice, or principle through Book II as a graph.",
                    "- Open the exact passage that supports a concept or relation.",
                    "- Use the full map as a navigation surface instead of a static picture.",
                ]
            )
        )
    with what_right:
        st.markdown("### Download the dataset")
        st.write(
            "Grab the structured Book II exports for NLP, graph analysis, or close reading "
            "outside the app."
        )
        _render_download_chooser(
            st,
            artifacts=download_artifacts,
            key_prefix="home-dataset",
        )


def _render_concept_view(
    st: Any,
    *,
    dataset: ViewerDataset,
    filters: ViewerFilters,
    filtered_concepts: list[ConceptAnnotation],
    selected_concept: ConceptAnnotation | None,
    graph_hops: int,
    pending_concept_key: str,
    pending_view_key: str,
    queue_concept: Callable[[str], None],
    queue_passage: Callable[[str], None],
) -> None:
    st.subheader("Concept Explorer")
    st.caption(
        "Start with the readable role a concept plays in Book II; open the data table "
        "only if you need the scaffolding underneath."
    )
    if selected_concept is None:
        st.info("Choose a concept from the sidebar.")
        return

    related_relations = sorted(
        filter_relations(dataset, filters, related_to_concept_id=selected_concept.id),
        key=lambda relation: relation_sort_key(
            relation,
            dataset,
            focal_concept_id=selected_concept.id,
        ),
    )
    outgoing_rows = [
        relation for relation in related_relations if relation.source_id == selected_concept.id
    ]
    incoming_rows = [
        relation for relation in related_relations if relation.target_id == selected_concept.id
    ]

    left_col, right_col = st.columns([1.3, 1])
    with left_col:
        st.markdown(f"## {selected_concept.primary_label}")
        st.write(selected_concept.description)
        st.markdown("### How this functions in Book II")
        st.markdown(concept_story_markdown(selected_concept, dataset))
        if selected_concept.notes:
            st.caption(selected_concept.notes)
    with right_col:
        _render_evidence_cards(
            st,
            concept=selected_concept,
            dataset=dataset,
            key_prefix=f"concept-evidence-{selected_concept.id}",
            queue_passage=queue_passage,
        )

    st.markdown("### Local concept map")
    ego_nodes, ego_relations = build_ego_graph(
        dataset,
        selected_concept.id,
        filters,
        hops=graph_hops,
    )
    if ego_nodes:
        map_left, map_right = st.columns([1.15, 0.85])
        with map_left:
            st.caption(
                f"Showing a compact {graph_hops}-hop neighborhood around "
                f"`{selected_concept.primary_label}`. Click any node to open it here."
            )
            clicked_concept_id = render_clickable_graph(
                graph_html=build_graph_html(
                    ego_nodes,
                    ego_relations,
                    center_concept_id=selected_concept.id,
                    height="360px",
                ),
                height="360px",
                key=f"concept-map-{selected_concept.id}-{graph_hops}",
            )
            if queue_graph_click_navigation(
                st.session_state,
                clicked_concept_id=clicked_concept_id,
                pending_concept_key=pending_concept_key,
                pending_view_key=pending_view_key,
                dataset=dataset,
            ):
                st.rerun()
        with map_right:
            st.markdown("#### In this neighborhood")
            st.markdown(
                "\n".join(
                    [
                        f"- {len(ego_nodes)} visible concepts",
                        f"- {len(ego_relations)} visible relations",
                        f"- Depth: {graph_hops} hop" + ("" if graph_hops == 1 else "s"),
                    ]
                )
            )
            st.caption(
                "Use this smaller map for close reading. Use Overall Map when you want the "
                "full filtered Book II network."
            )
    else:
        st.info("No local concept map matches the current filters.")

    relation_left, relation_right = st.columns(2)
    with relation_left:
        _render_relation_cards(
            st,
            title="Leads to",
            relations=outgoing_rows,
            dataset=dataset,
            selected_concept=selected_concept,
            key_prefix=f"outgoing-{selected_concept.id}",
            queue_concept=queue_concept,
            queue_passage=queue_passage,
        )
    with relation_right:
        _render_relation_cards(
            st,
            title="Comes into this concept",
            relations=incoming_rows,
            dataset=dataset,
            selected_concept=selected_concept,
            key_prefix=f"incoming-{selected_concept.id}",
            queue_concept=queue_concept,
            queue_passage=queue_passage,
        )

    with st.expander("Dataset details", expanded=False):
        st.dataframe(
            concept_detail_rows(selected_concept),
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("#### Evidence records")
        st.dataframe(
            evidence_rows(selected_concept, dataset),
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("#### Outgoing relations")
        st.dataframe(
            relation_rows(outgoing_rows, dataset),
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("#### Incoming relations")
        st.dataframe(
            relation_rows(incoming_rows, dataset),
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("#### Concepts matching current filters")
        st.dataframe(
            concept_summary_rows(filtered_concepts),
            use_container_width=True,
            hide_index=True,
        )


def _render_passage_view(
    st: Any,
    *,
    dataset: ViewerDataset,
    filtered_passages: list[PassageRecord],
    passage_choices: list[PassageRecord],
    passage_choice_ids: list[str],
    selected_passage_key: str,
    selected_passage_id: str | None,
    queue_concept: Callable[[str], None],
) -> None:
    st.subheader("Passage Explorer")
    st.caption(
        "Read a Book II passage in full, then see which concepts and relations the "
        "reviewed graph grounds there."
    )
    if not passage_choices or selected_passage_id is None:
        st.info("No passages match the current filters.")
        return

    visible_filtered_ids = {passage.passage_id for passage in filtered_passages}
    selected_passage_id = cast(
        str,
        st.selectbox(
            "Passage",
            options=passage_choice_ids,
            format_func=lambda passage_id: (
                f"{dataset.passage_index[passage_id].citation_label} ({passage_id})"
            ),
            key=selected_passage_key,
        ),
    )
    passage = dataset.passage_index[selected_passage_id]
    if selected_passage_id not in visible_filtered_ids:
        st.caption("Showing a focused passage outside the current section filter.")

    text_col, links_col = st.columns([1.4, 1])
    with text_col:
        st.markdown(f"## {passage.citation_label}")
        st.caption(
            f"Section {passage.chapter_or_section} · {passage.source_id} · {passage.passage_id}"
        )
        st.write(passage.text)

    passage_concepts = dataset.concepts_by_passage.get(passage.passage_id, ())
    passage_relations = dataset.relations_by_passage.get(passage.passage_id, ())
    with links_col:
        st.markdown("### Concepts grounded here")
        _render_passage_concept_cards(
            st,
            concepts=passage_concepts,
            key_prefix=f"passage-concept-{passage.passage_id}",
            queue_concept=queue_concept,
        )

    st.markdown("### Relations grounded here")
    if passage_relations:
        for relation in passage_relations:
            source_label = dataset.concept_index[relation.source_id].primary_label
            target_label = dataset.concept_index[relation.target_id].primary_label
            with st.container(border=True):
                st.markdown(
                    f"**{source_label} {_relation_label(relation.relation_type)} {target_label}**"
                )
                st.caption(relation.assertion_tier.replace("_", " "))
    else:
        st.caption("No relations currently cite this passage.")

    with st.expander("Structured passage details", expanded=False):
        st.dataframe(
            concept_summary_rows(list(passage_concepts)),
            use_container_width=True,
            hide_index=True,
        )
        st.dataframe(
            passage_relation_rows(passage_relations, dataset),
            use_container_width=True,
            hide_index=True,
        )

def _render_overall_map_view(
    st: Any,
    *,
    dataset: ViewerDataset,
    filters: ViewerFilters,
    selected_concept_id: str | None,
    pending_concept_key: str,
    pending_view_key: str,
) -> None:
    st.subheader("Overall Map")
    map_control_left, map_control_right, map_control_third = st.columns([1, 1, 1.25])
    with map_control_left:
        overall_show_edge_labels = st.toggle(
            "Show edge labels",
            value=False,
            key="avg-overall-edge-labels",
        )
    with map_control_right:
        overall_show_isolates = st.toggle(
            "Show isolated nodes",
            value=True,
            key="avg-overall-isolates",
        )
    with map_control_third:
        st.caption(
            "Click a node to jump into its concept page. Use the built-in Select and "
            "Filter menus inside the graph to search and trim the map."
        )

    overall_nodes, overall_relations = build_filtered_graph(
        dataset,
        filters,
        include_isolates=overall_show_isolates,
    )
    overall_node_ids = {concept.id for concept in overall_nodes}
    highlighted_concept_id = (
        selected_concept_id if selected_concept_id in overall_node_ids else None
    )
    overall_degree_rows = graph_degree_rows(overall_nodes, overall_relations)
    isolate_labels = [
        cast(str, row["label"])
        for row in overall_degree_rows
        if cast(int, row["total_degree"]) == 0
    ]
    relation_mix_rows: list[dict[str, object]] = [
        {"relation_type": relation_type, "count": count}
        for relation_type, count in sorted(
            Counter(relation.relation_type for relation in overall_relations).items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]

    if not overall_nodes:
        st.info("No concepts match the current filters for the overall map.")
        return

    overall_metrics = st.columns(4)
    overall_metrics[0].metric("Visible concepts", len(overall_nodes))
    overall_metrics[1].metric("Visible relations", len(overall_relations))
    overall_metrics[2].metric("Kinds in view", len({node.kind for node in overall_nodes}))
    overall_metrics[3].metric("Isolated nodes", len(isolate_labels))

    clicked_concept_id = render_clickable_graph(
        graph_html=build_graph_html(
            overall_nodes,
            overall_relations,
            center_concept_id=None,
            highlight_concept_id=highlighted_concept_id,
            graph_mode="overall",
            show_edge_labels=overall_show_edge_labels,
            height="760px",
        ),
        height="760px",
        key=f"overall-map-{overall_show_edge_labels}-{overall_show_isolates}",
    )
    if queue_graph_click_navigation(
        st.session_state,
        clicked_concept_id=clicked_concept_id,
        pending_concept_key=pending_concept_key,
        pending_view_key=pending_view_key,
        dataset=dataset,
    ):
        st.rerun()

    st.markdown("### Graph legend")
    st.markdown(
        kind_legend_html(sorted({concept.kind for concept in overall_nodes})),
        unsafe_allow_html=True,
    )

    summary_left, summary_right = st.columns(2)
    with summary_left:
        st.markdown("### Most connected concepts in view")
        st.dataframe(
            overall_degree_rows[:12],
            use_container_width=True,
            hide_index=True,
        )
    with summary_right:
        st.markdown("### Relation mix in view")
        st.dataframe(
            relation_mix_rows,
            use_container_width=True,
            hide_index=True,
        )


def _render_stats_view(st: Any, *, dataset: ViewerDataset) -> None:
    st.subheader("Stats")
    st.caption("The current public dataset is a fully reviewed Book II export.")
    stats_left, stats_right = st.columns(2)
    with stats_left:
        st.markdown("### Counts by concept kind")
        st.dataframe(
            [{"kind": kind, "count": count} for kind, count in concept_stats(dataset).items()],
            use_container_width=True,
            hide_index=True,
        )
    with stats_right:
        st.markdown("### Counts by relation type")
        st.dataframe(
            [
                {"relation_type": relation_type, "count": count}
                for relation_type, count in relation_stats(dataset).items()
            ],
            use_container_width=True,
            hide_index=True,
        )

    assertion_counts = Counter(
        [concept.assertion_tier for concept in dataset.concepts]
        + [relation.assertion_tier for relation in dataset.relations]
    )
    st.markdown("### Assertion tiers")
    st.dataframe(
        [
            {"assertion_tier": assertion_tier, "count": count}
            for assertion_tier, count in sorted(assertion_counts.items())
        ],
        use_container_width=True,
        hide_index=True,
    )


def render() -> None:
    try:
        st = importlib.import_module("streamlit")
    except ModuleNotFoundError as exc:
        msg = (
            "Streamlit is not installed. Install the viewer extras with "
            "`pip install -e \".[viewer]\"`."
        )
        raise SystemExit(msg) from exc

    logo_path = Path(__file__).resolve().parents[3] / "docs" / "assets" / "aristotle-head-icon.png"
    page_icon = str(logo_path) if logo_path.exists() else "🏛️"
    st.set_page_config(page_title="Aristotle Virtue Graph", page_icon=page_icon, layout="wide")

    try:
        dataset = load_viewer_dataset()
    except ViewerDataError as exc:
        st.error(str(exc))
        st.stop()

    download_artifacts = build_download_artifacts(dataset)

    concept_kinds = available_concept_kinds(dataset)
    relation_types = available_relation_types(dataset)
    assertion_tiers = available_assertion_tiers(dataset)
    active_view_key = "avg-active-view"
    pending_view_key = "avg-pending-view"
    selected_concept_key = "avg-selected-concept-id"
    pending_concept_key = "avg-pending-concept-id"
    selected_passage_key = "avg-selected-passage-id"
    pending_passage_key = "avg-pending-passage-id"

    apply_pending_concept_selection(
        st.session_state,
        selected_concept_key=selected_concept_key,
        pending_concept_key=pending_concept_key,
        dataset=dataset,
    )
    apply_pending_passage_selection(
        st.session_state,
        selected_passage_key=selected_passage_key,
        pending_passage_key=pending_passage_key,
        dataset=dataset,
    )
    apply_pending_view_navigation(
        st.session_state,
        active_view_key=active_view_key,
        pending_view_key=pending_view_key,
    )

    default_concept = default_concept_id(dataset, dataset.concepts)
    if (
        st.session_state.get(selected_concept_key) not in dataset.concept_index
        and default_concept is not None
    ):
        st.session_state[selected_concept_key] = default_concept

    header_left, header_right = st.columns([0.7, 7.3])
    with header_left:
        if logo_path.exists():
            st.image(str(logo_path), width=54)
    with header_right:
        st.title("Aristotle Virtue Graph")
        st.caption("Reviewed, passage-grounded explorer for Nicomachean Ethics Book II.")
        st.markdown("`Book II only` `45 passages` `54 concepts` `42 relations`")

    def on_queue_concept(concept_id: str) -> None:
        queue_concept_navigation(
            st.session_state,
            concept_id=concept_id,
            pending_concept_key=pending_concept_key,
            pending_view_key=pending_view_key,
        )

    def on_queue_passage(passage_id: str) -> None:
        queue_passage_navigation(
            st.session_state,
            passage_id=passage_id,
            pending_passage_key=pending_passage_key,
            pending_view_key=pending_view_key,
        )

    st.sidebar.caption("Reviewed Book II explorer")
    _render_download_chooser(
        st.sidebar,
        artifacts=download_artifacts,
        key_prefix="sidebar-dataset",
    )

    start_here_ids = start_here_concept_ids(dataset)
    if start_here_ids:
        st.sidebar.markdown("### Start here")
        for concept_id in start_here_ids:
            concept = dataset.concept_index[concept_id]
            st.sidebar.button(
                concept.primary_label,
                key=f"start-here-{concept_id}",
                use_container_width=True,
                on_click=on_queue_concept,
                args=(concept_id,),
            )

    selected_concept_id = cast(
        str,
        st.sidebar.selectbox(
            "Selected concept",
            options=[concept.id for concept in dataset.concepts],
            format_func=lambda concept_id: dataset.concept_index[concept_id].primary_label,
            key=selected_concept_key,
        ),
    )
    graph_hops = st.sidebar.radio(
        "Concept map depth",
        options=[1, 2],
        index=0,
        horizontal=True,
    )

    with st.sidebar.expander("Filters", expanded=False):
        search_text = st.text_input(
            "Concept search",
            placeholder="Search courage, pleasure, habit...",
        )
        selected_kinds = st.multiselect(
            "Concept kinds",
            options=concept_kinds,
            default=concept_kinds,
        )
        selected_relation_types = st.multiselect(
            "Relation types",
            options=relation_types,
            default=relation_types,
        )
        selected_tiers = st.multiselect(
            "Assertion tiers",
            options=assertion_tiers,
            default=assertion_tiers,
        )
        selected_sections = st.multiselect(
            "Book II sections",
            options=list(range(1, 10)),
            default=list(range(1, 10)),
        )

    filters = ViewerFilters(
        search_text=search_text,
        concept_kinds=frozenset(selected_kinds),
        relation_types=frozenset(selected_relation_types),
        assertion_tiers=frozenset(selected_tiers),
        sections=frozenset(selected_sections),
    )

    st.info(intro_markdown())
    metric_cols = st.columns(4)
    metric_cols[0].metric("Concepts", dataset.stats.get("concept_count", len(dataset.concepts)))
    metric_cols[1].metric("Relations", dataset.stats.get("relation_count", len(dataset.relations)))
    metric_cols[2].metric("Passages", dataset.stats.get("passage_count", len(dataset.passages)))
    metric_cols[3].metric("Dataset", "Reviewed")

    filtered_concepts = filter_concepts(dataset, filters)
    filtered_passages = filter_passages(dataset, filters)
    selected_concept = dataset.concept_index.get(selected_concept_id)

    focused_passage_id = cast(str | None, st.session_state.get(selected_passage_key))
    passage_choices = passage_options(
        dataset,
        filtered_passages,
        focused_passage_id=focused_passage_id,
    )
    passage_choice_ids = [passage.passage_id for passage in passage_choices]
    if passage_choice_ids and st.session_state.get(selected_passage_key) not in passage_choice_ids:
        concept_passage_ids = (
            evidence_passage_ids(selected_concept.evidence) if selected_concept is not None else []
        )
        matching_concept_passage = next(
            (passage_id for passage_id in concept_passage_ids if passage_id in passage_choice_ids),
            None,
        )
        st.session_state[selected_passage_key] = matching_concept_passage or passage_choice_ids[0]
    selected_passage_id = cast(str | None, st.session_state.get(selected_passage_key))

    active_view = cast(
        str,
        st.radio(
            "View",
            options=list(VIEW_NAMES),
            horizontal=True,
            label_visibility="collapsed",
            key=active_view_key,
        ),
    )

    if active_view == HOME_VIEW:
        _render_home_view(
            st,
            dataset=dataset,
            download_artifacts=download_artifacts,
            queue_concept=on_queue_concept,
            queue_passage=on_queue_passage,
        )
    elif active_view == CONCEPT_VIEW:
        _render_concept_view(
            st,
            dataset=dataset,
            filters=filters,
            filtered_concepts=filtered_concepts,
            selected_concept=selected_concept,
            graph_hops=graph_hops,
            pending_concept_key=pending_concept_key,
            pending_view_key=pending_view_key,
            queue_concept=on_queue_concept,
            queue_passage=on_queue_passage,
        )
    elif active_view == PASSAGE_VIEW:
        _render_passage_view(
            st,
            dataset=dataset,
            filtered_passages=filtered_passages,
            passage_choices=passage_choices,
            passage_choice_ids=passage_choice_ids,
            selected_passage_key=selected_passage_key,
            selected_passage_id=selected_passage_id,
            queue_concept=on_queue_concept,
        )
    elif active_view == OVERALL_MAP_VIEW:
        _render_overall_map_view(
            st,
            dataset=dataset,
            filters=filters,
            selected_concept_id=selected_concept_id,
            pending_concept_key=pending_concept_key,
            pending_view_key=pending_view_key,
        )
    elif active_view == STATS_VIEW:
        _render_stats_view(st, dataset=dataset)
