from __future__ import annotations

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


def intro_markdown() -> str:
    return (
        "This local viewer presents an evidence-first graph for *Nicomachean Ethics* Book II. "
        "Every concept and relation shown here is tied to one or more passage ids. "
        "Candidate mode shows machine-assisted draft annotations; approved mode is reserved for "
        "human-reviewed material only. To promote reviewed items, move them from the candidate "
        "files into the matching approved files and rerun the strict export commands."
    )


def kind_color(kind: str) -> str:
    return _KIND_COLORS.get(kind, "#6c757d")


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


def build_graph_html(
    nodes: list[ConceptAnnotation],
    relations: list[RelationAnnotation],
    *,
    center_concept_id: str,
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

    network = Network(
        height="540px",
        width="100%",
        directed=True,
        notebook=False,
        bgcolor="#ffffff",
        font_color="#111111",
        cdn_resources="in_line",
    )
    network.barnes_hut()

    for concept in nodes:
        tooltip = escape(
            "\n".join(
                [
                    f"Label: {concept.primary_label}",
                    f"Kind: {concept.kind}",
                    f"Tier: {concept.assertion_tier}",
                    f"Sections: {', '.join(str(section) for section in concept.sections)}",
                ]
            )
        ).replace("\n", "<br>")
        network.add_node(
            concept.id,
            label=concept.primary_label,
            title=tooltip,
            color=kind_color(concept.kind),
            size=34 if concept.id == center_concept_id else 22,
            borderWidth=3 if concept.id == center_concept_id else 1,
        )

    for relation in relations:
        tooltip = escape(
            "\n".join(
                [
                    f"Relation: {relation.relation_type}",
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
            label=relation.relation_type,
            title=tooltip,
            arrows="to",
            color="#9aa5b1",
        )

    network.set_options(
        """
        const options = {
          "interaction": {"hover": true, "navigationButtons": true},
          "physics": {"stabilization": {"iterations": 200}},
          "edges": {"font": {"size": 12, "align": "middle"}}
        }
        """
    )
    return cast(str, network.generate_html())
