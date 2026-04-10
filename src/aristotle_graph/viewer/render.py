from __future__ import annotations

import json
from html import escape
from typing import Any, cast

from aristotle_graph.annotations.models import ConceptAnnotation, RelationAnnotation
from aristotle_graph.viewer.load import ViewerDataset

_KIND_COLORS = {
    "virtue": "#2a9d8f",
    "vice": "#e76f51",
    "domain": "#457b9d",
    "principle": "#8d99ae",
    "state": "#3d5a80",
    "faculty": "#6d597a",
    "passion": "#f4a261",
    "process": "#90be6d",
    "action": "#577590",
    "person": "#264653",
    "condition": "#b56576",
}

_EDGE_COLORS = {
    "approved": "#34506b",
    "candidate": "#9aa5b1",
}


def intro_markdown() -> str:
    return (
        "Every concept and relation shown here is grounded in one or more "
        "*Nicomachean Ethics* Book II passages. "
        "Candidate mode shows the broader working layer; approved mode shows the reviewed core."
    )


def kind_color(kind: str) -> str:
    return _KIND_COLORS.get(kind, "#6c757d")


def edge_color(review_status: str) -> str:
    return _EDGE_COLORS.get(review_status, "#9aa5b1")


def relation_rows(
    relations: list[RelationAnnotation],
    dataset: ViewerDataset,
) -> list[dict[str, Any]]:
    def concept_label(concept_id: str) -> str:
        concept = dataset.concept_index.get(concept_id)
        return concept.primary_label if concept is not None else concept_id

    rows: list[dict[str, Any]] = []
    for relation in relations:
        rows.append(
            {
                "relation_type": relation.relation_type,
                "source": concept_label(relation.source_id),
                "target": concept_label(relation.target_id),
                "assertion_tier": relation.assertion_tier,
                "review_status": relation.review_status,
                "evidence_passage_ids": ", ".join(
                    evidence.passage_id for evidence in relation.evidence
                ),
            }
        )
    return rows


def concept_summary_rows(
    concepts: list[ConceptAnnotation],
) -> list[dict[str, Any]]:
    return [
        {
            "label": concept.primary_label,
            "id": concept.id,
            "kind": concept.kind,
            "assertion_tier": concept.assertion_tier,
            "review_status": concept.review_status,
            "sections": ", ".join(str(section) for section in concept.sections),
        }
        for concept in concepts
    ]


def evidence_rows(concept: ConceptAnnotation) -> list[dict[str, str]]:
    return [
        {
            "passage_id": evidence.passage_id,
            "support_type": evidence.support_type,
            "note": evidence.note,
            "quote_excerpt": evidence.quote_excerpt or "",
        }
        for evidence in concept.evidence
    ]


def passage_relation_rows(
    relations: tuple[RelationAnnotation, ...],
) -> list[dict[str, str]]:
    return [
        {
            "relation_type": relation.relation_type,
            "source_id": relation.source_id,
            "target_id": relation.target_id,
            "review_status": relation.review_status,
            "assertion_tier": relation.assertion_tier,
        }
        for relation in relations
    ]


def kind_legend_html(kinds: list[str]) -> str:
    chips = []
    for kind in kinds:
        chips.append(
            "<span style=\"display:inline-flex;align-items:center;gap:0.45rem;"
            "padding:0.35rem 0.7rem;margin:0 0.45rem 0.45rem 0;border-radius:999px;"
            "background:#ffffff;border:1px solid #d7dfeb;color:#1f2f44;font-size:0.92rem;\">"
            f"<span style=\"width:0.8rem;height:0.8rem;border-radius:999px;"
            f"background:{kind_color(kind)};display:inline-block;\"></span>"
            f"{escape(kind.replace('-', ' ').title())}</span>"
        )
    return "".join(chips)


def build_graph_html(
    nodes: list[ConceptAnnotation],
    relations: list[RelationAnnotation],
    *,
    center_concept_id: str | None,
    highlight_concept_id: str | None = None,
    graph_mode: str = "ego",
    show_edge_labels: bool = True,
    height: str = "540px",
) -> str:
    try:
        from pyvis.network import Network
    except ModuleNotFoundError:
        return (
            "<div style='padding:1rem;border:1px solid #ddd;border-radius:8px;'>"
            "Install the viewer extra to render the graph view: "
            "<code>pip install -e \".[viewer]\"</code>."
            "</div>"
        )

    is_overall_map = graph_mode == "overall"
    network = Network(
        height=height,
        width="100%",
        directed=True,
        notebook=False,
        neighborhood_highlight=is_overall_map,
        select_menu=is_overall_map,
        filter_menu=is_overall_map,
        bgcolor="#fbf8f2" if is_overall_map else "#ffffff",
        font_color="#1f2f44",
        cdn_resources="in_line",
    )
    if is_overall_map:
        network.barnes_hut(
            gravity=-4200,
            central_gravity=0.22,
            spring_length=145,
            spring_strength=0.04,
            damping=0.2,
            overlap=0.15,
        )
    else:
        network.barnes_hut(
            gravity=-3000,
            central_gravity=0.26,
            spring_length=120,
            spring_strength=0.05,
            damping=0.18,
            overlap=0.1,
        )

    degree_counts: dict[str, int] = {}
    for relation in relations:
        degree_counts[relation.source_id] = degree_counts.get(relation.source_id, 0) + 1
        degree_counts[relation.target_id] = degree_counts.get(relation.target_id, 0) + 1
    max_degree = max(degree_counts.values(), default=1)
    emphasized_concept_id = highlight_concept_id or center_concept_id

    for concept in nodes:
        degree = degree_counts.get(concept.id, 0)
        degree_ratio = degree / max_degree if max_degree else 0
        size = 18 + (16 * degree_ratio)
        if concept.id == center_concept_id:
            size += 12
        elif concept.id == emphasized_concept_id:
            size += 7
        tooltip = escape(
            "\n".join(
                [
                    f"Label: {concept.primary_label}",
                    f"Kind: {concept.kind}",
                    f"Tier: {concept.assertion_tier}",
                    f"Review: {concept.review_status}",
                    f"Degree: {degree}",
                    f"Sections: {', '.join(str(section) for section in concept.sections)}",
                    f"Evidence count: {len(concept.evidence)}",
                    f"Description: {concept.description}",
                ]
            )
        ).replace("\n", "<br>")
        network.add_node(
            concept.id,
            label=concept.primary_label,
            title=tooltip,
            group=concept.kind,
            color={
                "background": kind_color(concept.kind),
                "border": "#1f2f44" if concept.review_status == "approved" else "#c98b4a",
                "highlight": {
                    "background": kind_color(concept.kind),
                    "border": "#0b1824",
                },
            },
            size=size,
            borderWidth=(
                4
                if concept.id == center_concept_id
                else 2.5 if concept.id == emphasized_concept_id else 1.5
            ),
            borderWidthSelected=5,
            font={
                "face": "Georgia, serif",
                "size": 17 if is_overall_map else 15,
                "color": "#16324f",
                "strokeWidth": 4,
                "strokeColor": "#fbf8f2" if is_overall_map else "#ffffff",
            },
            mass=1 + degree_ratio,
        )

    for relation in relations:
        relation_label = relation.relation_type.replace("_", " ")
        tooltip = escape(
            "\n".join(
                [
                    f"Relation: {relation_label}",
                    f"Tier: {relation.assertion_tier}",
                    f"Review: {relation.review_status}",
                    "Evidence: "
                    + ", ".join(evidence.passage_id for evidence in relation.evidence),
                ]
            )
        ).replace("\n", "<br>")
        network.add_edge(
            relation.source_id,
            relation.target_id,
            label=relation_label if show_edge_labels else "",
            title=tooltip,
            arrows="to",
            color=edge_color(relation.review_status),
            dashes=relation.review_status != "approved",
            width=2.4 if relation.review_status == "approved" else 1.8,
        )

    options = {
        "interaction": {
            "hover": True,
            "navigationButtons": True,
            "keyboard": {"enabled": True, "bindToWindow": False},
            "tooltipDelay": 110,
            "multiselect": is_overall_map,
            "selectConnectedEdges": False,
        },
        "layout": {"improvedLayout": True},
        "physics": {
            "stabilization": {
                "enabled": True,
                "iterations": 420 if is_overall_map else 220,
                "fit": True,
            },
        },
        "nodes": {
            "shape": "dot",
            "shadow": {"enabled": is_overall_map, "size": 10, "x": 0, "y": 3},
        },
        "edges": {
            "smooth": {
                "enabled": True,
                "type": "dynamic" if is_overall_map else "continuous",
                "roundness": 0.22 if is_overall_map else 0.14,
            },
            "font": {
                "size": 11 if is_overall_map else 12,
                "align": "middle",
                "face": "Georgia, serif",
                "strokeWidth": 5,
                "strokeColor": "#fbf8f2" if is_overall_map else "#ffffff",
            },
        },
    }
    network.set_options(json.dumps(options))
    return cast(str, network.generate_html())
