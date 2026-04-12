from __future__ import annotations

import importlib
from collections import Counter
from collections.abc import Callable, MutableMapping
from html import escape
from pathlib import Path
from typing import Any, cast

from aristotle_graph.annotations.models import ConceptAnnotation, RelationAnnotation
from aristotle_graph.schemas import PassageRecord
from aristotle_graph.viewer.downloads import DownloadArtifact, build_download_artifacts
from aristotle_graph.viewer.graph_component import render_clickable_graph
from aristotle_graph.viewer.load import ViewerDataError, ViewerDataset, load_viewer_dataset
from aristotle_graph.viewer.render import (
    build_graph_html,
    bullet_list_html,
    concept_detail_rows,
    concept_role_line,
    concept_story_markdown,
    concept_summary_rows,
    evidence_rows,
    hero_html,
    kind_legend_html,
    meta_pills_html,
    passage_preview,
    passage_relation_rows,
    prose_panel_html,
    ranking_rows_html,
    reading_panel_html,
    relation_card_headline,
    relation_rows,
    relation_sentence,
    section_heading_html,
    selected_concept_context_markdown,
    simple_card_html,
    stat_grid_html,
    step_cards_html,
    triad_strip_html,
    viewer_shell_css,
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
    filter_summary_text,
    graph_degree_rows,
    home_concept_ids,
    home_passage_id,
    passage_navigation_targets,
    relation_sort_key,
    relation_stats,
)

HOME_VIEW, CONCEPT_VIEW, PASSAGE_VIEW, OVERALL_MAP_VIEW, STATS_VIEW = VIEW_NAMES


def _format_file_size(size_bytes: int) -> str:
    thresholds = (
        (1024 * 1024, "MB"),
        (1024, "KB"),
    )
    for divisor, suffix in thresholds:
        if size_bytes >= divisor:
            return f"{size_bytes / divisor:.1f} {suffix}"
    return f"{size_bytes} B"


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


def _relation_caption(relation: RelationAnnotation, dataset: ViewerDataset) -> str:
    passage_ids = evidence_passage_ids(relation.evidence)
    if not passage_ids:
        return relation.assertion_tier.replace("_", " ")
    passage = dataset.passage_index[passage_ids[0]]
    return f"{passage.citation_label} · {relation.assertion_tier.replace('_', ' ')}"


def _small_helper_html(text: str) -> str:
    return f"<div class='avg-helper'>{escape(text)}</div>"


def _join_labels(labels: list[str]) -> str:
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return ", ".join(labels[:-1]) + f", and {labels[-1]}"


def _section_label(sections: list[int]) -> str:
    ordered = sorted(set(sections))
    if not ordered:
        return "Book II"
    if len(ordered) == 1:
        return f"Section {ordered[0]}"
    return "Sections " + ", ".join(str(section) for section in ordered)


def _context_card_html(
    *,
    title: str,
    body: str,
    kicker: str | None = None,
    detail: str | None = None,
) -> str:
    kicker_html = (
        f"<div class='avg-kicker'>{escape(kicker)}</div>" if kicker is not None else ""
    )
    detail_html = (
        f"<div class='avg-context-detail'>{escape(detail)}</div>" if detail is not None else ""
    )
    return (
        "<div class='avg-context'>"
        f"{kicker_html}"
        f"<div class='avg-context-title'>{escape(title)}</div>"
        f"<p>{escape(body)}</p>"
        f"{detail_html}"
        "</div>"
    )


def _empty_state_html(title: str, body: str) -> str:
    return simple_card_html(title=title, body=body)


def _home_passage_card_copy(
    dataset: ViewerDataset,
    passage_id: str,
) -> tuple[str, str, str]:
    passage = dataset.passage_index[passage_id]
    if passage_id == "ne.b2.s7.p1":
        return (
            f"Read {passage.citation_label}",
            (
                f"Passage-first route: start with {passage.citation_label}, where Aristotle "
                "lays out courage, cowardice, rashness, and fear and confidence."
            ),
            f"Read {passage.citation_label}",
        )

    linked_labels = [
        concept.primary_label for concept in dataset.concepts_by_passage.get(passage_id, ())
    ][:4]
    if linked_labels:
        body = (
            f"Passage-first route: start with {passage.citation_label} on "
            f"{_join_labels(linked_labels)}."
        )
    else:
        body = f"Passage-first route: start with {passage.citation_label}."
    return (f"Read {passage.citation_label}", body, f"Read {passage.citation_label}")


def _render_download_chooser(
    st: Any,
    *,
    artifacts: tuple[DownloadArtifact, ...],
    key_prefix: str,
) -> None:
    artifact_index = {artifact.key: artifact for artifact in artifacts}
    default_key = artifacts[0].key
    with st.popover("Download dataset"):
        st.markdown(
            _small_helper_html(
                "Choose the full bundle or one processed file from data/processed/."
            ),
            unsafe_allow_html=True,
        )
        selected_key = cast(
            str,
            st.selectbox(
                "Dataset file",
                options=[artifact.key for artifact in artifacts],
                format_func=lambda artifact_key: artifact_index[artifact_key].label,
                key=f"{key_prefix}-download-choice",
                label_visibility="collapsed",
            ),
        )
        selected_artifact = artifact_index.get(selected_key, artifact_index[default_key])
        st.markdown(
            _small_helper_html(
                f"{selected_artifact.filename} · {_format_file_size(selected_artifact.size_bytes)}"
            ),
            unsafe_allow_html=True,
        )
        st.write(selected_artifact.description)
        st.download_button(
            f"Download {selected_artifact.filename}",
            data=selected_artifact.payload,
            file_name=selected_artifact.filename,
            mime=selected_artifact.mime,
            width="stretch",
            key=f"{key_prefix}-download-{selected_artifact.key}",
            on_click="ignore",
        )


def _render_relation_cards(
    st: Any,
    *,
    title: str,
    body: str,
    relations: list[RelationAnnotation],
    dataset: ViewerDataset,
    focal_concept: ConceptAnnotation,
    key_prefix: str,
    queue_concept: Callable[[str], None],
    queue_passage: Callable[[str], None],
) -> None:
    st.markdown(section_heading_html(title=title, body=body, level=3), unsafe_allow_html=True)
    if not relations:
        st.markdown(
            _empty_state_html(
                title="Nothing under the current filters",
                body="Broaden the filters or move through the local map to surface nearby links.",
            ),
            unsafe_allow_html=True,
        )
        return

    for relation in relations:
        is_outgoing = relation.source_id == focal_concept.id
        other_concept_id = relation.target_id if is_outgoing else relation.source_id
        passage_ids = evidence_passage_ids(relation.evidence)
        headline = relation_card_headline(
            relation,
            dataset,
            focal_concept_id=focal_concept.id,
        )
        with st.container(border=True):
            st.markdown(
                simple_card_html(
                    title=headline,
                    body=_relation_caption(relation, dataset),
                    eyebrow=relation.relation_type.replace("_", " "),
                ),
                unsafe_allow_html=True,
            )
            action_left, action_right = st.columns(2)
            action_left.button(
                "Open concept",
                key=f"{key_prefix}-concept-{relation.id}",
                width="stretch",
                type="secondary",
                on_click=queue_concept,
                args=(other_concept_id,),
            )
            if passage_ids:
                action_right.button(
                    "Read supporting passage",
                    key=f"{key_prefix}-passage-{relation.id}",
                    width="stretch",
                    type="primary",
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
    st.markdown(
        section_heading_html(
            title="Supporting passages",
            body=(
                "Open a short passage card when you want to move from the concept "
                "back into the text."
            ),
            level=3,
        ),
        unsafe_allow_html=True,
    )
    if not concept.evidence:
        st.markdown(
            _empty_state_html(
                title="No supporting passages",
                body=(
                    "This concept currently has no linked evidence cards in the "
                    "processed dataset."
                ),
            ),
            unsafe_allow_html=True,
        )
        return

    visible_evidence = concept.evidence[:3]
    for evidence in visible_evidence:
        passage = dataset.passage_index[evidence.passage_id]
        with st.container(border=True):
            st.markdown(
                simple_card_html(
                    title=passage.citation_label,
                    body=passage_preview(passage.text, limit=170),
                    eyebrow=f"Section {passage.chapter_or_section}",
                ),
                unsafe_allow_html=True,
            )
            st.markdown(_small_helper_html(evidence.note), unsafe_allow_html=True)
            st.button(
                "Read supporting passage",
                key=f"{key_prefix}-{evidence.passage_id}",
                width="stretch",
                type="primary",
                on_click=queue_passage,
                args=(evidence.passage_id,),
            )
    if len(concept.evidence) > len(visible_evidence):
        st.markdown(
            _small_helper_html(
                f"Showing the first {len(visible_evidence)} passage cards for this concept."
            ),
            unsafe_allow_html=True,
        )


def _render_home_view(
    st: Any,
    *,
    dataset: ViewerDataset,
    download_artifacts: tuple[DownloadArtifact, ...],
    queue_concept: Callable[[str], None],
    queue_passage: Callable[[str], None],
) -> None:
    steps = [
        "Open one route that matches the kind of question you have.",
        "Inspect the nearby structure rather than reading the graph as a wall of labels.",
        "Open the supporting passage and check the exact text behind the claim.",
    ]
    st.markdown(
        section_heading_html(
            title="Start here",
            body=(
                "Choose a route that matches what you want to understand first."
            ),
        ),
        unsafe_allow_html=True,
    )
    st.markdown(step_cards_html(steps), unsafe_allow_html=True)

    entry_concepts = home_concept_ids(dataset)
    first_concept = entry_concepts[0] if entry_concepts else None
    second_concept = entry_concepts[1] if len(entry_concepts) > 1 else None
    focus_passage_id = home_passage_id(dataset)
    entry_left, entry_mid, entry_right = st.columns(3)

    if first_concept is not None:
        with entry_left:
            st.markdown(
                simple_card_html(
                    title="Courage",
                    body=(
                        "Specific virtue: see one triad through its deficiency, its excess, "
                        "and the field it concerns."
                    ),
                    eyebrow="Specific virtue",
                ),
                unsafe_allow_html=True,
            )
            st.button(
                "Open courage",
                key="home-courage",
                width="stretch",
                type="primary",
                on_click=queue_concept,
                args=(first_concept,),
            )

    if second_concept is not None:
        with entry_mid:
            second_title = dataset.concept_index[second_concept].primary_label
            st.markdown(
                simple_card_html(
                    title=second_title,
                    body=(
                        "Formation route: start with the process that explains how Book II says "
                        "character is acquired."
                    ),
                    eyebrow="Formation route",
                ),
                unsafe_allow_html=True,
            )
            st.button(
                f"Open {second_title.lower()}",
                key=f"home-{second_concept}",
                width="stretch",
                type="secondary",
                on_click=queue_concept,
                args=(second_concept,),
            )

    if focus_passage_id is not None:
        passage_title, passage_body, passage_button = _home_passage_card_copy(
            dataset,
            focus_passage_id,
        )
        with entry_right:
            st.markdown(
                simple_card_html(
                    title=passage_title,
                    body=passage_body,
                    eyebrow="Passage-first reading",
                ),
                unsafe_allow_html=True,
            )
            st.button(
                passage_button,
                key="home-passage",
                width="stretch",
                type="secondary",
                on_click=queue_passage,
                args=(focus_passage_id,),
            )

    reuse_left, reuse_right = st.columns([1.15, 0.85])
    with reuse_left:
        st.markdown(
            section_heading_html(
                title="What you can do here",
                body=(
                    "Use the reviewed Book II dataset as a reading aid, not just a schema browser."
                ),
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            bullet_list_html(
                [
                    "Compare one virtue with its neighboring vices and its domain.",
                    "Move from a graph link straight to the passage that supports it.",
                    "Reuse the processed exports outside the app for close reading or graph work.",
                ]
            ),
            unsafe_allow_html=True,
        )
    with reuse_right:
        st.markdown(
            section_heading_html(
                title="Reuse the dataset",
                body=(
                    "Download the committed Book II exports when you want the structured files "
                    "outside the viewer."
                ),
            ),
            unsafe_allow_html=True,
        )
        _render_download_chooser(
            st,
            artifacts=download_artifacts,
            key_prefix="home",
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
    st.markdown(
        section_heading_html(
            title="Concept Explorer",
            body=(
                "Open one concept, understand its role in Book II, then move outward through "
                "supporting passages and nearby links."
            ),
        ),
        unsafe_allow_html=True,
    )
    if selected_concept is None:
        st.markdown(
            _empty_state_html(
                title="Open a concept",
                body="Use the sidebar to choose one concept and trace how Book II structures it.",
            ),
            unsafe_allow_html=True,
        )
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

    concept_meta = [
        selected_concept.kind.replace("-", " ").title(),
        _section_label(list(selected_concept.sections)),
        f"{len(selected_concept.evidence)} supporting passages",
    ]

    lead_col, evidence_col = st.columns([1.18, 0.82])
    with lead_col:
        st.markdown(
            _context_card_html(
                title=selected_concept.primary_label,
                body=concept_role_line(selected_concept, dataset),
                kicker=selected_concept.kind.replace("-", " "),
                detail=selected_concept.description,
            ),
            unsafe_allow_html=True,
        )
        st.markdown(meta_pills_html(concept_meta), unsafe_allow_html=True)
        triad_html = triad_strip_html(selected_concept, dataset)
        if triad_html:
            st.markdown(triad_html, unsafe_allow_html=True)
        st.markdown(
            prose_panel_html(
                title="How this functions in Book II",
                body=concept_story_markdown(selected_concept, dataset),
                eyebrow="Deterministic reading summary",
            ),
            unsafe_allow_html=True,
        )
        if selected_concept.notes:
            st.markdown(_small_helper_html(selected_concept.notes), unsafe_allow_html=True)

    with evidence_col:
        _render_evidence_cards(
            st,
            concept=selected_concept,
            dataset=dataset,
            key_prefix=f"concept-evidence-{selected_concept.id}",
            queue_passage=queue_passage,
        )

    map_col, relation_col = st.columns([0.88, 1.12])
    with map_col:
        st.markdown(
            section_heading_html(
                title="Local map",
                body=(
                    "Use this smaller neighborhood for nearby moves; use the overall map when "
                    "you want the whole Book II network."
                ),
                level=3,
            ),
            unsafe_allow_html=True,
        )
        show_edge_labels = st.toggle(
            "Show relation labels on the local map",
            value=False,
            key=f"concept-edge-labels-{selected_concept.id}",
        )
        ego_nodes, ego_relations = build_ego_graph(
            dataset,
            selected_concept.id,
            filters,
            hops=graph_hops,
        )
        if ego_nodes:
            clicked_concept_id = render_clickable_graph(
                graph_html=build_graph_html(
                    ego_nodes,
                    ego_relations,
                    center_concept_id=selected_concept.id,
                    show_edge_labels=show_edge_labels,
                    height="300px",
                ),
                height="300px",
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
            st.markdown(
                _small_helper_html(
                    f"Showing a {graph_hops}-hop neighborhood around "
                    f"{selected_concept.primary_label}. Every visible node is clickable."
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                _empty_state_html(
                    title="No local map under the current filters",
                    body="Broaden the filters or move to the overall map for a wider view.",
                ),
                unsafe_allow_html=True,
            )

    with relation_col:
        _render_relation_cards(
            st,
            title="Direct links outward",
            body="These are the direct links Book II gives this concept under the current filters.",
            relations=outgoing_rows,
            dataset=dataset,
            focal_concept=selected_concept,
            key_prefix=f"outgoing-{selected_concept.id}",
            queue_concept=queue_concept,
            queue_passage=queue_passage,
        )
        _render_relation_cards(
            st,
            title="Direct links inward",
            body="These are the nearby ideas that point into the selected concept.",
            relations=incoming_rows,
            dataset=dataset,
            focal_concept=selected_concept,
            key_prefix=f"incoming-{selected_concept.id}",
            queue_concept=queue_concept,
            queue_passage=queue_passage,
        )

    with st.expander("Dataset details", expanded=False):
        st.dataframe(
            concept_detail_rows(selected_concept),
            width="stretch",
            hide_index=True,
        )
        st.markdown("#### Evidence records")
        st.dataframe(
            evidence_rows(selected_concept, dataset),
            width="stretch",
            hide_index=True,
        )
        st.markdown("#### Outgoing relations")
        st.dataframe(
            relation_rows(outgoing_rows, dataset),
            width="stretch",
            hide_index=True,
        )
        st.markdown("#### Incoming relations")
        st.dataframe(
            relation_rows(incoming_rows, dataset),
            width="stretch",
            hide_index=True,
        )
        st.markdown("#### Concepts matching the current filters")
        st.dataframe(
            concept_summary_rows(filtered_concepts),
            width="stretch",
            hide_index=True,
        )


def _render_passage_view(
    st: Any,
    *,
    dataset: ViewerDataset,
    filtered_passages: list[PassageRecord],
    selected_passage_id: str | None,
    queue_concept: Callable[[str], None],
    queue_passage: Callable[[str], None],
) -> None:
    st.markdown(
        section_heading_html(
            title="Passage Explorer",
            body="Read the text first, then see which concepts and relations are grounded here.",
        ),
        unsafe_allow_html=True,
    )
    if selected_passage_id is None or selected_passage_id not in dataset.passage_index:
        st.markdown(
            _empty_state_html(
                title="Open a supporting passage",
                body="Use the sidebar or any concept evidence card to move directly into the text.",
            ),
            unsafe_allow_html=True,
        )
        return

    passage = dataset.passage_index[selected_passage_id]
    prev_passage_id, next_passage_id = passage_navigation_targets(
        filtered_passages,
        selected_passage_id,
    )

    nav_left, nav_mid, nav_right = st.columns([1, 1.5, 1])
    nav_left.button(
        "Previous passage",
        key=f"prev-passage-{selected_passage_id}",
        width="stretch",
        type="secondary",
        disabled=prev_passage_id is None,
        on_click=queue_passage,
        args=(prev_passage_id,) if prev_passage_id is not None else (),
    )
    nav_mid.markdown(
        _context_card_html(
            title=passage.citation_label,
            body=f"Section {passage.chapter_or_section} · {passage.passage_id}",
            kicker="Supporting passage",
            detail=(
                "Read the text first, then use the linked cards to move back "
                "into the concept layer."
            ),
        ),
        unsafe_allow_html=True,
    )
    nav_right.button(
        "Next passage",
        key=f"next-passage-{selected_passage_id}",
        width="stretch",
        type="secondary",
        disabled=next_passage_id is None,
        on_click=queue_passage,
        args=(next_passage_id,) if next_passage_id is not None else (),
    )

    visible_filtered_ids = {passage_record.passage_id for passage_record in filtered_passages}
    if selected_passage_id not in visible_filtered_ids:
        st.markdown(
            _small_helper_html(
                "This supporting passage is outside the current section filter. "
                "Previous and next navigation follow only the visible filtered "
                "passage sequence."
            ),
            unsafe_allow_html=True,
        )

    text_col, links_col = st.columns([1.28, 0.72])
    with text_col:
        st.markdown(
            reading_panel_html(
                title=passage.citation_label,
                meta=f"Book II · Section {passage.chapter_or_section} · {passage.passage_id}",
                lead=(
                    "Stay with the wording here first, then use the linked "
                    "concepts and relations to see what the graph claims are "
                    "grounded in this passage."
                ),
                text=passage.text,
            ),
            unsafe_allow_html=True,
        )

    passage_concepts = dataset.concepts_by_passage.get(passage.passage_id, ())
    passage_relations = dataset.relations_by_passage.get(passage.passage_id, ())
    with links_col:
        st.markdown(
            section_heading_html(
                title="Concepts grounded here",
                body="Move from the text back into the concept layer.",
                level=3,
            ),
            unsafe_allow_html=True,
        )
        if passage_concepts:
            for concept in passage_concepts:
                with st.container(border=True):
                    st.markdown(
                        simple_card_html(
                            title=concept.primary_label,
                            body=concept_role_line(concept, dataset),
                            eyebrow=concept.kind.replace("-", " "),
                        ),
                        unsafe_allow_html=True,
                    )
                    st.button(
                        "Open concept",
                        key=f"passage-concept-{passage.passage_id}-{concept.id}",
                        width="stretch",
                        type="primary",
                        on_click=queue_concept,
                        args=(concept.id,),
                    )
        else:
            st.markdown(
                _empty_state_html(
                    title="No linked concepts",
                    body=(
                        "No concept cards are attached to this passage in the "
                        "current processed dataset."
                    ),
                ),
                unsafe_allow_html=True,
            )

        st.markdown(
            section_heading_html(
                title="Relations grounded here",
                body="These are the graph claims that cite this passage.",
                level=3,
            ),
            unsafe_allow_html=True,
        )
        if passage_relations:
            for relation in passage_relations:
                with st.container(border=True):
                    st.markdown(
                        simple_card_html(
                            title=relation_sentence(relation, dataset).capitalize(),
                            body=_relation_caption(relation, dataset),
                            eyebrow="Grounded relation",
                        ),
                        unsafe_allow_html=True,
                    )
        else:
            st.markdown(
                _empty_state_html(
                    title="No linked relations",
                    body="No relation cards currently cite this supporting passage.",
                ),
                unsafe_allow_html=True,
            )

    with st.expander("Dataset details", expanded=False):
        st.dataframe(
            concept_summary_rows(list(passage_concepts)),
            width="stretch",
            hide_index=True,
        )
        st.dataframe(
            passage_relation_rows(passage_relations, dataset),
            width="stretch",
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
    st.markdown(
        section_heading_html(
            title="Overall Map",
            body=(
                "Use the whole network when you want to compare clusters or "
                "move across Book II from any visible node."
            ),
        ),
        unsafe_allow_html=True,
    )
    map_control_left, map_control_right, map_control_third = st.columns([1, 1, 1.4])
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
        st.markdown(
            _small_helper_html(
                "Every visible concept node is clickable and opens its concept page."
            ),
            unsafe_allow_html=True,
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
    relation_mix_rows = [
        {"relation_type": relation_type, "count": count}
        for relation_type, count in sorted(
            Counter(relation.relation_type for relation in overall_relations).items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]

    if not overall_nodes:
        st.markdown(
            _empty_state_html(
                title="No visible concepts",
                body="Broaden the filters to bring more of Book II back into view.",
            ),
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        stat_grid_html(
            [
                ("Visible concepts", str(len(overall_nodes))),
                ("Visible relations", str(len(overall_relations))),
                (
                    "Selected concept",
                    dataset.concept_index[selected_concept_id].primary_label
                    if selected_concept_id in dataset.concept_index
                    else "None",
                ),
            ]
        ),
        unsafe_allow_html=True,
    )

    clicked_concept_id = render_clickable_graph(
        graph_html=build_graph_html(
            overall_nodes,
            overall_relations,
            center_concept_id=None,
            highlight_concept_id=highlighted_concept_id,
            graph_mode="overall",
            show_edge_labels=overall_show_edge_labels,
            height="700px",
        ),
        height="700px",
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

    st.markdown(
        kind_legend_html(sorted({concept.kind for concept in overall_nodes})),
        unsafe_allow_html=True,
    )

    summary_left, summary_right = st.columns([1, 1])
    selected_context = (
        dataset.concept_index[highlighted_concept_id]
        if highlighted_concept_id is not None
        else None
    )
    with summary_left:
        st.markdown(
            section_heading_html(
                title="Selected concept in context",
                body=(
                    "Use this as a quick anchor while you move through the "
                    "larger Book II network."
                ),
                level=3,
            ),
            unsafe_allow_html=True,
        )
        if selected_context is None:
            st.markdown(
                _empty_state_html(
                    title="No concept selected",
                    body=(
                        "Click any visible node in the map to open it here "
                        "and move into its concept page."
                    ),
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                _context_card_html(
                    title=selected_context.primary_label,
                    body=concept_role_line(selected_context, dataset),
                    kicker=selected_context.kind.replace("-", " "),
                    detail=selected_context.description,
                ),
                unsafe_allow_html=True,
            )
            triad_html = triad_strip_html(selected_context, dataset)
            if triad_html:
                st.markdown(triad_html, unsafe_allow_html=True)
            st.markdown(
                prose_panel_html(
                    title="How this concept sits in the current map",
                    body=selected_concept_context_markdown(selected_context, dataset).replace(
                        "**", ""
                    ),
                ),
                unsafe_allow_html=True,
            )
    with summary_right:
        st.markdown(
            section_heading_html(
                title="Most connected concepts in view",
                body="A quick way to spot hubs in the current filtered map.",
                level=3,
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            ranking_rows_html(
                [
                    (
                        str(row["label"]),
                        f"{row['total_degree']} links",
                    )
                    for row in overall_degree_rows[:10]
                ]
            ),
            unsafe_allow_html=True,
        )

    with st.expander("Relation mix in view", expanded=False):
        st.markdown(
            ranking_rows_html(
                [
                    (str(row["relation_type"]).replace("_", " "), f"{row['count']}")
                    for row in relation_mix_rows
                ]
            ),
            unsafe_allow_html=True,
        )


def _render_stats_view(st: Any, *, dataset: ViewerDataset) -> None:
    concept_kind_rows = [
        (kind.replace("-", " ").title(), str(count))
        for kind, count in concept_stats(dataset).items()
    ]
    relation_type_rows = [
        (relation_type.replace("_", " "), str(count))
        for relation_type, count in relation_stats(dataset).items()
    ]
    assertion_counts = Counter(
        [concept.assertion_tier for concept in dataset.concepts]
        + [relation.assertion_tier for relation in dataset.relations]
    )

    st.markdown(
        section_heading_html(
            title="Stats",
            body="These counts describe the reviewed Book II dataset currently loaded in the app.",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        stat_grid_html(
            [
                ("Passages", str(len(dataset.passages))),
                ("Concepts", str(len(dataset.concepts))),
                ("Relations", str(len(dataset.relations))),
                ("Relation types", str(len(relation_type_rows))),
            ]
        ),
        unsafe_allow_html=True,
    )
    stats_left, stats_right = st.columns(2)
    with stats_left:
        st.markdown(
            section_heading_html(
                title="Counts by concept kind",
                body=(
                    "A quick view of how Book II is distributed across "
                    "virtues, vices, principles, domains, and related kinds."
                ),
                level=3,
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            ranking_rows_html(concept_kind_rows),
            unsafe_allow_html=True,
        )
    with stats_right:
        st.markdown(
            section_heading_html(
                title="Counts by relation type",
                body="This is the relation mix the reviewed Book II graph currently uses.",
                level=3,
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            ranking_rows_html(relation_type_rows),
            unsafe_allow_html=True,
        )

    st.markdown(
        section_heading_html(
            title="Assertion tiers",
            body=(
                "These counts show how much of the dataset is textual, "
                "editorial normalization, or interpretive."
            ),
            level=3,
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        ranking_rows_html(
            [
                (assertion_tier.replace("_", " "), str(count))
                for assertion_tier, count in sorted(assertion_counts.items())
            ]
        ),
        unsafe_allow_html=True,
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
    search_key = "avg-filter-search"
    kinds_key = "avg-filter-kinds"
    relation_types_key = "avg-filter-relation-types"
    tiers_key = "avg-filter-assertion-tiers"
    sections_key = "avg-filter-sections"

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
    default_passage = home_passage_id(dataset)
    if (
        st.session_state.get(selected_concept_key) not in dataset.concept_index
        and default_concept is not None
    ):
        st.session_state[selected_concept_key] = default_concept
    if (
        st.session_state.get(selected_passage_key) not in dataset.passage_index
        and default_passage is not None
    ):
        st.session_state[selected_passage_key] = default_passage

    if search_key not in st.session_state:
        st.session_state[search_key] = ""
    if kinds_key not in st.session_state:
        st.session_state[kinds_key] = concept_kinds
    if relation_types_key not in st.session_state:
        st.session_state[relation_types_key] = relation_types
    if tiers_key not in st.session_state:
        st.session_state[tiers_key] = assertion_tiers
    if sections_key not in st.session_state:
        st.session_state[sections_key] = list(range(1, 10))

    def _filters_from_state() -> ViewerFilters:
        return ViewerFilters(
            search_text=cast(str, st.session_state.get(search_key, "")),
            concept_kinds=frozenset(
                cast(list[str], st.session_state.get(kinds_key, concept_kinds))
            ),
            relation_types=frozenset(
                cast(list[str], st.session_state.get(relation_types_key, relation_types))
            ),
            assertion_tiers=frozenset(
                cast(list[str], st.session_state.get(tiers_key, assertion_tiers))
            ),
            sections=frozenset(
                cast(list[int], st.session_state.get(sections_key, list(range(1, 10))))
            ),
        )

    preview_filters = _filters_from_state()

    def on_sidebar_concept_change() -> None:
        st.session_state[pending_view_key] = CONCEPT_VIEW

    def on_sidebar_passage_change() -> None:
        st.session_state[pending_view_key] = PASSAGE_VIEW

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

    st.markdown(viewer_shell_css(), unsafe_allow_html=True)
    st.markdown(
        hero_html(
            title="Aristotle Virtue Graph",
            subtitle=None,
            chips=[],
        ),
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown(
            section_heading_html(
                title="Explore",
                body=(
                    "Open one concept or one supporting passage first. Use "
                    "filters only when you want to narrow the view."
                ),
                level=3,
            ),
            unsafe_allow_html=True,
        )
        st.selectbox(
            "Open concept",
            options=[concept.id for concept in dataset.concepts],
            format_func=lambda concept_id: dataset.concept_index[concept_id].primary_label,
            key=selected_concept_key,
            on_change=on_sidebar_concept_change,
        )
        st.selectbox(
            "Jump to passage",
            options=[passage.passage_id for passage in dataset.passages],
            format_func=lambda passage_id: dataset.passage_index[passage_id].citation_label,
            key=selected_passage_key,
            on_change=on_sidebar_passage_change,
        )
        graph_hops = st.radio(
            "Local map depth",
            options=[1, 2],
            index=0,
            horizontal=True,
            format_func=lambda value: "1 hop" if value == 1 else "2 hops",
        )
        st.markdown(
            (
                "<div class='avg-filter-summary'>"
                f"{escape(filter_summary_text(dataset, preview_filters))}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        with st.expander("Filters", expanded=False):
            st.text_input(
                "Concept search",
                placeholder="Search courage, pleasure, habit...",
                key=search_key,
            )
            st.multiselect(
                "Concept kinds",
                options=concept_kinds,
                key=kinds_key,
            )
            st.multiselect(
                "Relation types",
                options=relation_types,
                key=relation_types_key,
            )
            st.multiselect(
                "Assertion tiers",
                options=assertion_tiers,
                key=tiers_key,
            )
            st.multiselect(
                "Book II sections",
                options=list(range(1, 10)),
                key=sections_key,
            )
        st.divider()
        st.markdown(
            section_heading_html(
                title="Download dataset",
                body=(
                    "Choose the processed files you want to keep outside the viewer."
                ),
                level=3,
            ),
            unsafe_allow_html=True,
        )
        _render_download_chooser(
            st,
            artifacts=download_artifacts,
            key_prefix="sidebar",
        )

    filters = _filters_from_state()
    filtered_concepts = filter_concepts(dataset, filters)
    filtered_passages = filter_passages(dataset, filters)
    selected_concept_id = cast(str | None, st.session_state.get(selected_concept_key))
    selected_concept = (
        dataset.concept_index[selected_concept_id]
        if selected_concept_id in dataset.concept_index
        else None
    )
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
            selected_passage_id=selected_passage_id,
            queue_concept=on_queue_concept,
            queue_passage=on_queue_passage,
        )
    elif active_view == OVERALL_MAP_VIEW:
        _render_overall_map_view(
            st,
            dataset=dataset,
            filters=filters,
            selected_concept_id=selected_concept.id if selected_concept is not None else None,
            pending_concept_key=pending_concept_key,
            pending_view_key=pending_view_key,
        )
    else:
        _render_stats_view(st, dataset=dataset)
