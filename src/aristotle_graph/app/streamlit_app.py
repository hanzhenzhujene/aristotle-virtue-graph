from __future__ import annotations

import importlib
from typing import cast

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
    ViewerFilters,
    available_assertion_tiers,
    available_concept_kinds,
    available_relation_types,
    build_ego_graph,
    default_concept_id,
    filter_concepts,
    filter_passages,
    filter_relations,
)


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

    st.set_page_config(page_title="Aristotle Virtue Graph", layout="wide")
    st.title("Aristotle Virtue Graph")
    st.caption("Evidence-first local explorer for Nicomachean Ethics Book II.")

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

    st.sidebar.caption(
        "Tip: start with `courage`, then switch between candidate and approved mode."
    )

    st.sidebar.markdown("### Filters")
    search_text = st.sidebar.text_input(
        "Concept search",
        placeholder="Search courage, pleasure, habit...",
    )
    selected_kinds = st.sidebar.multiselect(
        "Concept kinds",
        options=concept_kinds,
        default=concept_kinds,
    )
    selected_relation_types = st.sidebar.multiselect(
        "Relation types",
        options=relation_types,
        default=relation_types,
    )
    selected_tiers = st.sidebar.multiselect(
        "Assertion tiers",
        options=assertion_tiers,
        default=assertion_tiers,
    )
    selected_sections = st.sidebar.multiselect(
        "Book II sections",
        options=list(range(1, 10)),
        default=list(range(1, 10)),
    )
    graph_hops = st.sidebar.radio("Graph depth", options=[1, 2], index=0, horizontal=True)

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

    default_concept = default_concept_id(dataset, filtered_concepts)
    concept_options = {concept.primary_label: concept.id for concept in filtered_concepts}
    concept_labels = list(concept_options.keys()) if concept_options else ["No matching concepts"]
    selected_index = 0
    if default_concept is not None:
        for index, label in enumerate(concept_labels):
            if concept_options.get(label) == default_concept:
                selected_index = index
                break
    selected_concept_label = st.sidebar.selectbox(
        "Selected concept",
        options=concept_labels,
        index=selected_index,
    )
    selected_concept_id = concept_options.get(selected_concept_label, default_concept)

    concept_tab, passage_tab, graph_tab, stats_tab = st.tabs(
        ["Concept Explorer", "Passage Explorer", "Graph View", "Stats"]
    )

    with concept_tab:
        st.subheader("Concept Explorer")
        if not filtered_concepts:
            st.info("No concepts match the current filters.")
        else:
            selected_concept = (
                dataset.concept_index[selected_concept_id]
                if selected_concept_id is not None
                else None
            )
            if selected_concept is None:
                st.info("Choose a concept from the sidebar.")
            else:
                section_labels = ", ".join(
                    str(section) for section in selected_concept.sections
                )
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
                        width="stretch",
                        hide_index=True,
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
                        width="stretch",
                        hide_index=True,
                    )
                with relation_right:
                    st.markdown("#### Incoming relations")
                    st.dataframe(
                        relation_rows(incoming_rows, dataset),
                        width="stretch",
                        hide_index=True,
                    )

                st.markdown("#### Filtered concepts")
                st.dataframe(
                    concept_summary_rows(filtered_concepts),
                    width="stretch",
                    hide_index=True,
                )

    with passage_tab:
        st.subheader("Passage Explorer")
        if not filtered_passages:
            st.info("No passages match the current section filter.")
        else:
            passage_options = {
                f"{passage.citation_label} ({passage.passage_id})": passage.passage_id
                for passage in filtered_passages
            }
            selected_passage_label = st.selectbox(
                "Passage",
                options=list(passage_options.keys()),
                index=0,
            )
            selected_passage_id = passage_options[selected_passage_label]
            passage = dataset.passage_index[selected_passage_id]

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
                        width="stretch",
                        hide_index=True,
                    )
                else:
                    st.caption("No concepts currently cite this passage.")
            with linked_right:
                st.markdown("#### Relations grounded here")
                if passage_relations:
                    st.dataframe(
                        passage_relation_rows(passage_relations),
                        width="stretch",
                        hide_index=True,
                    )
                else:
                    st.caption("No relations currently cite this passage.")

    with graph_tab:
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
                    width="stretch",
                    hide_index=True,
                )

    with stats_tab:
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
