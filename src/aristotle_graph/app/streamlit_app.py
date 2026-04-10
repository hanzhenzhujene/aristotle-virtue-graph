from __future__ import annotations

import importlib
from collections.abc import MutableMapping
from pathlib import Path
from typing import cast

from aristotle_graph.annotations.models import RelationAnnotation
from aristotle_graph.viewer.load import ReviewMode, ViewerDataError, load_viewer_dataset
from aristotle_graph.viewer.render import (
    build_graph_html,
    concept_summary_rows,
    evidence_rows,
    intro_markdown,
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
    default_concept_id,
    evidence_passage_ids,
    filter_concepts,
    filter_passages,
    filter_relations,
    passage_options,
    start_here_concept_ids,
)


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
        session_state[active_view_key] = VIEW_NAMES[0]


def render() -> None:
    try:
        st = importlib.import_module("streamlit")
        components = importlib.import_module("streamlit.components.v1")
    except ModuleNotFoundError as exc:
        msg = (
            "Streamlit is not installed. Install the viewer extras with "
            "`pip install -e \".[viewer]\"`."
        )
        raise SystemExit(msg) from exc

    logo_path = Path(__file__).resolve().parents[3] / "docs" / "assets" / "aristotle-head-icon.png"
    page_icon = str(logo_path) if logo_path.exists() else "🏛️"
    st.set_page_config(page_title="Aristotle Virtue Graph", page_icon=page_icon, layout="wide")

    header_left, header_right = st.columns([0.7, 7.3])
    with header_left:
        if logo_path.exists():
            st.image(str(logo_path), width=54)
    with header_right:
        st.title("Aristotle Virtue Graph")
        st.caption("Evidence-first explorer for Nicomachean Ethics Book II.")
        st.markdown("`Book II only` `45 passages` `candidate + approved`")

    mode = cast(
        ReviewMode,
        st.sidebar.radio(
            "Review mode",
            options=["candidate", "approved"],
            index=0,
            format_func=lambda value: value.title(),
        ),
    )

    try:
        dataset = load_viewer_dataset(mode=mode)
    except ViewerDataError as exc:
        st.error(str(exc))
        st.stop()

    concept_kinds = available_concept_kinds(dataset)
    relation_types = available_relation_types(dataset)
    assertion_tiers = available_assertion_tiers(dataset)
    active_view_key = "avg-active-view"
    pending_view_key = "avg-pending-view"
    selected_concept_key = f"avg-selected-concept-label-{mode}"
    selected_passage_key = f"avg-selected-passage-id-{mode}"

    st.sidebar.caption(
        "Start with `courage`, then compare `candidate` and `approved`."
    )
    default_concept = default_concept_id(dataset, list(dataset.concepts))
    concept_options = {concept.primary_label: concept.id for concept in dataset.concepts}
    concept_labels = list(concept_options.keys()) if concept_options else ["No concepts available"]
    default_concept_label = concept_labels[0]
    if default_concept is not None:
        for label, concept_id in concept_options.items():
            if concept_id == default_concept:
                default_concept_label = label
                break
    if st.session_state.get(selected_concept_key) not in concept_options:
        st.session_state[selected_concept_key] = default_concept_label
    apply_pending_view_navigation(
        st.session_state,
        active_view_key=active_view_key,
        pending_view_key=pending_view_key,
    )

    def set_selected_concept(concept_id: str) -> None:
        st.session_state[selected_concept_key] = dataset.concept_index[concept_id].primary_label
        st.session_state[pending_view_key] = VIEW_NAMES[0]

    def focus_passage(passage_id: str) -> None:
        st.session_state[selected_passage_key] = passage_id
        st.session_state[pending_view_key] = VIEW_NAMES[1]

    start_here_ids = start_here_concept_ids(dataset)
    if start_here_ids:
        st.sidebar.markdown("### Start here")
        for concept_id in start_here_ids:
            concept = dataset.concept_index[concept_id]
            st.sidebar.button(
                concept.primary_label,
                key=f"start-here-{mode}-{concept_id}",
                use_container_width=True,
                on_click=set_selected_concept,
                args=(concept_id,),
            )

    selected_concept_label = st.sidebar.selectbox(
        "Selected concept",
        options=concept_labels,
        key=selected_concept_key,
    )
    graph_hops = st.sidebar.radio("Graph depth", options=[1, 2], index=0, horizontal=True)

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

    if dataset.empty_notice is not None:
        st.warning(dataset.empty_notice)

    metric_cols = st.columns(4)
    metric_cols[0].metric(
        "Concepts",
        dataset.stats.get("concept_count", len(dataset.concepts)),
    )
    metric_cols[1].metric(
        "Relations",
        dataset.stats.get("relation_count", len(dataset.relations)),
    )
    metric_cols[2].metric(
        "Passages",
        dataset.stats.get("passage_count", len(dataset.passages)),
    )
    metric_cols[3].metric("Mode", "Approved" if mode == "approved" else "Candidate")

    filtered_concepts = filter_concepts(dataset, filters)
    filtered_passages = filter_passages(dataset, filters)
    selected_concept_id = concept_options.get(selected_concept_label, default_concept)
    selected_concept = (
        dataset.concept_index[selected_concept_id]
        if selected_concept_id is not None
        else None
    )
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

    def render_evidence_shortcuts(passage_ids: list[str], *, key_prefix: str) -> None:
        if not passage_ids:
            return
        st.caption("Open supporting passage")
        for passage_id in passage_ids:
            passage = dataset.passage_index[passage_id]
            st.button(
                f"Open {passage.citation_label}",
                key=f"{key_prefix}-{passage_id}",
                use_container_width=True,
                on_click=focus_passage,
                args=(passage_id,),
            )

    def render_relation_shortcuts(
        relations: list[RelationAnnotation],
        *,
        key_prefix: str,
    ) -> None:
        if not relations:
            return
        st.caption("Jump to supporting passage")
        for relation in relations:
            relation_passage_ids = evidence_passage_ids(relation.evidence)
            if not relation_passage_ids:
                continue
            passage_id = relation_passage_ids[0]
            passage = dataset.passage_index[passage_id]
            source_label = dataset.concept_index[relation.source_id].primary_label
            target_label = dataset.concept_index[relation.target_id].primary_label
            relation_label = relation.relation_type.replace("_", " ")
            st.button(
                f"{passage.citation_label}: {source_label} {relation_label} {target_label}",
                key=f"{key_prefix}-{relation.id}",
                use_container_width=True,
                on_click=focus_passage,
                args=(passage_id,),
            )

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

    if active_view == VIEW_NAMES[0]:
        st.subheader("Concept Explorer")
        if selected_concept is None:
            st.info("Choose a concept from the sidebar.")
        else:
            section_labels = ", ".join(str(section) for section in selected_concept.sections)
            source_labels = ", ".join(selected_concept.source_labels)
            alias_labels = (
                ", ".join(selected_concept.aliases)
                if selected_concept.aliases
                else "None"
            )
            left_col, right_col = st.columns([1.3, 1])
            with left_col:
                st.markdown(f"### {selected_concept.primary_label}")
                st.write(selected_concept.description)
                st.markdown(
                    "\n".join(
                        [
                            f"- `id`: `{selected_concept.id}`",
                            f"- `kind`: `{selected_concept.kind}`",
                            f"- `assertion tier`: `{selected_concept.assertion_tier}`",
                            f"- `review status`: `{selected_concept.review_status}`",
                            f"- `sections`: {section_labels}",
                            f"- `source labels`: {source_labels}",
                            f"- `aliases`: {alias_labels}",
                        ]
                    )
                )
                if selected_concept.notes:
                    st.caption(selected_concept.notes)
            with right_col:
                st.markdown("#### Evidence")
                st.dataframe(
                    evidence_rows(selected_concept),
                    use_container_width=True,
                    hide_index=True,
                )
                render_evidence_shortcuts(
                    evidence_passage_ids(selected_concept.evidence),
                    key_prefix=f"concept-evidence-{selected_concept.id}",
                )

            outgoing_relations = filter_relations(
                dataset,
                filters,
                related_to_concept_id=selected_concept.id,
            )
            incoming_rows = [
                relation
                for relation in outgoing_relations
                if relation.target_id == selected_concept.id
            ]
            outgoing_rows = [
                relation
                for relation in outgoing_relations
                if relation.source_id == selected_concept.id
            ]

            relation_left, relation_right = st.columns(2)
            with relation_left:
                st.markdown("#### Outgoing relations")
                st.dataframe(
                    relation_rows(outgoing_rows, dataset),
                    use_container_width=True,
                    hide_index=True,
                )
                render_relation_shortcuts(
                    outgoing_rows,
                    key_prefix=f"outgoing-relation-{selected_concept.id}",
                )
            with relation_right:
                st.markdown("#### Incoming relations")
                st.dataframe(
                    relation_rows(incoming_rows, dataset),
                    use_container_width=True,
                    hide_index=True,
                )
                render_relation_shortcuts(
                    incoming_rows,
                    key_prefix=f"incoming-relation-{selected_concept.id}",
                )

            st.markdown("#### Filtered concepts")
            if filtered_concepts:
                st.dataframe(
                    concept_summary_rows(filtered_concepts),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.caption("No concepts match the current filters.")

    elif active_view == VIEW_NAMES[1]:
        st.subheader("Passage Explorer")
        if not passage_choices or selected_passage_id is None:
            st.info("No passages match the current section filter.")
        else:
            visible_filtered_ids = {passage.passage_id for passage in filtered_passages}
            selected_passage_id = cast(
                str,
                st.selectbox(
                    "Passage",
                    options=passage_choice_ids,
                    format_func=(
                        lambda passage_id: (
                            f"{dataset.passage_index[passage_id].citation_label} ({passage_id})"
                        )
                    ),
                    key=selected_passage_key,
                ),
            )
            passage = dataset.passage_index[selected_passage_id]
            if selected_passage_id not in visible_filtered_ids:
                st.caption(
                    "Showing a focused passage outside the current section filter."
                )

            st.markdown(f"### {passage.citation_label}")
            st.markdown(
                "\n".join(
                    [
                        f"- `passage id`: `{passage.passage_id}`",
                        f"- `section`: `{passage.chapter_or_section}`",
                        f"- `source`: `{passage.source_id}`",
                        f"- `citation`: `{passage.citation_label}`",
                    ]
                )
            )
            st.write(passage.text)

            passage_concepts = dataset.concepts_by_passage.get(passage.passage_id, ())
            passage_relations = dataset.relations_by_passage.get(passage.passage_id, ())

            linked_left, linked_right = st.columns(2)
            with linked_left:
                st.markdown("#### Concepts grounded here")
                if passage_concepts:
                    st.dataframe(
                        concept_summary_rows(list(passage_concepts)),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.caption("No concepts currently cite this passage.")
            with linked_right:
                st.markdown("#### Relations grounded here")
                if passage_relations:
                    st.dataframe(
                        passage_relation_rows(passage_relations),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.caption("No relations currently cite this passage.")

    elif active_view == VIEW_NAMES[2]:
        st.subheader("Graph View")
        if selected_concept_id is None:
            st.info("Choose a concept from the sidebar to render an ego graph.")
        else:
            ego_nodes, ego_relations = build_ego_graph(
                dataset,
                selected_concept_id,
                filters,
                hops=graph_hops,
            )
            if not ego_nodes:
                st.info("No graph neighborhood matches the current filters.")
            else:
                st.caption(
                    f"Showing a {graph_hops}-hop neighborhood around "
                    f"`{dataset.concept_index[selected_concept_id].primary_label}`."
                )
                components.html(
                    build_graph_html(
                        ego_nodes,
                        ego_relations,
                        center_concept_id=selected_concept_id,
                    ),
                    height=560,
                    scrolling=False,
                )
                st.dataframe(
                    relation_rows(ego_relations, dataset),
                    use_container_width=True,
                    hide_index=True,
                )

    else:
        st.subheader("Stats")
        metric_cols = st.columns(3)
        metric_cols[0].metric(
            "Concepts",
            dataset.stats.get("concept_count", len(dataset.concepts)),
        )
        metric_cols[1].metric(
            "Relations",
            dataset.stats.get("relation_count", len(dataset.relations)),
        )
        metric_cols[2].metric(
            "Passages",
            dataset.stats.get("passage_count", len(dataset.passages)),
        )

        left_stats, right_stats = st.columns(2)
        with left_stats:
            st.markdown("#### Concepts by kind")
            st.json(dataset.stats.get("concept_kinds", {}))
            st.markdown("#### Review statuses")
            st.json(dataset.stats.get("concept_review_statuses", {}))
        with right_stats:
            st.markdown("#### Relations by type")
            st.json(dataset.stats.get("relation_types", {}))
            st.markdown("#### Relation review statuses")
            st.json(dataset.stats.get("relation_review_statuses", {}))


if __name__ == "__main__":
    render()
