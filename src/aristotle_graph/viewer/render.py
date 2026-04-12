from __future__ import annotations

import json
from html import escape
from typing import Any

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


def intro_markdown(book_label: str = "Book II") -> str:
    return (
        f"This dashboard turns *Nicomachean Ethics* {book_label} into a reviewed, "
        "passage-grounded map. Move from a concept to its relations, then open the "
        "exact passage that supports the structure you see."
    )


def kind_color(kind: str) -> str:
    return _KIND_COLORS.get(kind, "#6c757d")


def edge_color(review_status: str) -> str:
    return _EDGE_COLORS.get(review_status, "#9aa5b1")


def _join_labels(labels: list[str]) -> str:
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return ", ".join(labels[:-1]) + f", and {labels[-1]}"


def _join_clauses(clauses: list[str]) -> str:
    if not clauses:
        return ""
    if len(clauses) == 1:
        return clauses[0]
    if len(clauses) == 2:
        return f"{clauses[0]} and {clauses[1]}"
    return ", ".join(clauses[:-1]) + f", and {clauses[-1]}"


def _with_indefinite_article(label: str) -> str:
    lowered = label.lower()
    if lowered.startswith(("a ", "an ", "the ")):
        return label
    article = "an" if lowered[:1] in {"a", "e", "i", "o", "u"} else "a"
    return f"{article} {label}"


def _target_labels(
    concept_id: str,
    dataset: ViewerDataset,
    relation_type: str,
) -> list[str]:
    labels: list[str] = []
    for relation in dataset.outgoing_relations.get(concept_id, ()):
        if relation.relation_type != relation_type:
            continue
        labels.append(dataset.concept_index[relation.target_id].primary_label)
    return sorted(labels, key=str.lower)


def _incoming_labels(
    concept_id: str,
    dataset: ViewerDataset,
    relation_type: str,
) -> list[str]:
    return sorted(
        [
            dataset.concept_index[relation.source_id].primary_label
            for relation in dataset.incoming_relations.get(concept_id, ())
            if relation.relation_type == relation_type
        ],
        key=str.lower,
    )


def _unique_labels(labels: list[str]) -> list[str]:
    return sorted(set(labels), key=str.lower)


def _role_key(concept: ConceptAnnotation, dataset: ViewerDataset) -> str:
    outgoing_types = {
        relation.relation_type for relation in dataset.outgoing_relations.get(concept.id, ())
    }
    incoming_types = {
        relation.relation_type for relation in dataset.incoming_relations.get(concept.id, ())
    }

    if {"has_deficiency", "has_excess"} & outgoing_types:
        return "virtue-triad"
    if {"has_deficiency", "has_excess"} & incoming_types:
        return "vice"
    if "concerns" in incoming_types and not outgoing_types:
        return "domain"
    if concept.id in {"moral-virtue", "ethical-mean"}:
        return "principle"
    if concept.kind in {
        "principle",
        "process",
        "state",
        "faculty",
        "passion",
        "condition",
        "person",
    }:
        return "principle"
    return "general"


def _job_sentence(
    concept: ConceptAnnotation,
    *,
    role_key: str,
    book_label: str,
) -> str | None:
    if concept.id == "moral-virtue":
        return (
            f"Its job in {book_label} is to connect habit, pleasure, pain, and stable character "
            "before Aristotle turns to the particular virtues."
        )
    if concept.id == "ethical-mean":
        return (
            f"Its job in {book_label} is to show that virtue is not a flat midpoint, but something "
            "guided by judgment against excess and deficiency."
        )
    if concept.id == "habituation":
        return (
            f"Its job in {book_label} is to explain how character is acquired through repeated "
            "practice rather than handed over fully formed."
        )
    if role_key == "virtue-triad":
        return (
            f"Its job in {book_label} is to make the doctrine of the mean concrete by locating "
            "virtue within a field and between two opposed failures."
        )
    if role_key == "vice":
        return f"Its job in {book_label} is to mark one of the ways a virtue can miss the mean."
    if role_key == "domain":
        return (
            f"Its job in {book_label} is to show that virtues and vices are always judged within "
            "some field of feeling or action."
        )
    if role_key == "principle":
        return (
            f"Its job in {book_label} is to clarify the structure that makes the later virtue "
            "triads intelligible."
        )
    return None


def _guided_relation_sentence(
    concept: ConceptAnnotation,
    dataset: ViewerDataset,
) -> str | None:
    label = concept.primary_label
    concern_labels = _target_labels(concept.id, dataset, "concerns")
    is_a_labels = _target_labels(concept.id, dataset, "is_a")
    formed_by_labels = _target_labels(concept.id, dataset, "formed_by")
    requires_labels = _target_labels(concept.id, dataset, "requires")
    determined_by_labels = _target_labels(concept.id, dataset, "determined_by")
    contrasted_with_labels = _target_labels(concept.id, dataset, "contrasted_with")
    opposed_to_labels = _target_labels(concept.id, dataset, "opposed_to")

    clauses: list[str] = []
    if contrasted_with_labels:
        clauses.append(f"contrasts {label} with {_join_labels(contrasted_with_labels)}")
    if formed_by_labels:
        clauses.append(f"says {label} is formed by {_join_labels(formed_by_labels)}")
    if is_a_labels:
        is_a_phrase = (
            _with_indefinite_article(is_a_labels[0])
            if len(is_a_labels) == 1
            else _join_labels(is_a_labels)
        )
        clauses.append(f"classifies {label} as {is_a_phrase}")
    if concern_labels:
        clauses.append(f"ties {label} to {_join_labels(concern_labels)}")
    if determined_by_labels:
        clauses.append(f"says {label} is determined by {_join_labels(determined_by_labels)}")
    if requires_labels:
        clauses.append(f"says {label} requires {_join_labels(requires_labels)}")
    if opposed_to_labels:
        clauses.append(f"treats {label} as opposed to {_join_labels(opposed_to_labels)}")

    if not clauses:
        return None
    return f"{dataset.profile.book_label} {_join_clauses(clauses)}."


def _virtue_story(concept: ConceptAnnotation, dataset: ViewerDataset) -> str:
    label = concept.primary_label
    deficiency_labels = _target_labels(concept.id, dataset, "has_deficiency")
    excess_labels = _target_labels(concept.id, dataset, "has_excess")
    concern_labels = _target_labels(concept.id, dataset, "concerns")

    sentences = [
        (
            f"In {dataset.profile.book_label}, {label} is the virtue concerned "
            f"with {_join_labels(concern_labels)}."
        )
        if concern_labels
        else f"In {dataset.profile.book_label}, {label} is treated as a virtue."
    ]
    if deficiency_labels or excess_labels:
        parts: list[str] = []
        if deficiency_labels:
            parts.append(f"its deficiency is {_join_labels(deficiency_labels)}")
        if excess_labels:
            parts.append(f"its excess is {_join_labels(excess_labels)}")
        sentences.append(f"Aristotle positions it so that {', and '.join(parts)}.")
    job_sentence = _job_sentence(
        concept,
        role_key="virtue-triad",
        book_label=dataset.profile.book_label,
    )
    if job_sentence is not None:
        sentences.append(job_sentence)
    return "\n\n".join(sentences)


def _vice_story(concept: ConceptAnnotation, dataset: ViewerDataset) -> str:
    label = concept.primary_label
    deficiency_sources = _incoming_labels(concept.id, dataset, "has_deficiency")
    excess_sources = _incoming_labels(concept.id, dataset, "has_excess")
    source_ids = [
        relation.source_id
        for relation in dataset.incoming_relations.get(concept.id, ())
        if relation.relation_type in {"has_deficiency", "has_excess"}
    ]
    domain_labels = _unique_labels(
        [
            domain_label
            for source_id in source_ids
            for domain_label in _target_labels(source_id, dataset, "concerns")
        ]
    )

    if deficiency_sources:
        first_sentence = (
            f"In {dataset.profile.book_label}, {label} appears as the deficiency opposed to "
            f"{_join_labels(deficiency_sources)}."
        )
    elif excess_sources:
        first_sentence = (
            f"In {dataset.profile.book_label}, {label} appears as the excess opposed to "
            f"{_join_labels(excess_sources)}."
        )
    else:
        first_sentence = concept.description

    sentences = [first_sentence]
    if domain_labels:
        sentences.append(f"It belongs to the same field of {_join_labels(domain_labels)}.")
    job_sentence = _job_sentence(
        concept,
        role_key="vice",
        book_label=dataset.profile.book_label,
    )
    if job_sentence is not None:
        sentences.append(job_sentence)
    return "\n\n".join(sentences)


def _domain_story(concept: ConceptAnnotation, dataset: ViewerDataset) -> str:
    label = concept.primary_label
    source_labels = _incoming_labels(concept.id, dataset, "concerns")
    if source_labels:
        lead = (
            f"In {dataset.profile.book_label}, {label} is the field in which "
            f"{_join_labels(source_labels)} is assessed."
        )
    else:
        lead = concept.description

    sentences = [lead]
    job_sentence = _job_sentence(
        concept,
        role_key="domain",
        book_label=dataset.profile.book_label,
    )
    if job_sentence is not None:
        sentences.append(job_sentence)
    return "\n\n".join(sentences)


def concept_story_markdown(concept: ConceptAnnotation, dataset: ViewerDataset) -> str:
    role_key = _role_key(concept, dataset)
    if role_key == "virtue-triad":
        return _virtue_story(concept, dataset)
    if role_key == "vice":
        return _vice_story(concept, dataset)
    if role_key == "domain":
        return _domain_story(concept, dataset)

    paragraphs = [concept.description]
    guided_sentence = _guided_relation_sentence(concept, dataset)
    if guided_sentence is not None and guided_sentence != concept.description:
        paragraphs.append(guided_sentence)
    job_sentence = _job_sentence(
        concept,
        role_key=role_key,
        book_label=dataset.profile.book_label,
    )
    if job_sentence is not None:
        paragraphs.append(job_sentence)
    return "\n\n".join(paragraphs)


def relation_headline(
    relation: RelationAnnotation,
    dataset: ViewerDataset,
    *,
    focal_concept_id: str,
) -> str:
    is_outgoing = relation.source_id == focal_concept_id
    other_concept_id = relation.target_id if is_outgoing else relation.source_id
    other_label = dataset.concept_index[other_concept_id].primary_label

    if is_outgoing:
        templates = {
            "concerns": f"This concept concerns {other_label}",
            "has_deficiency": f"Its deficiency is {other_label}",
            "has_excess": f"Its excess is {other_label}",
            "formed_by": f"It is formed by {other_label}",
            "is_a": f"It is treated as {other_label}",
            "requires": f"It requires {other_label}",
            "determined_by": f"It is determined by {other_label}",
            "contrasted_with": f"{dataset.profile.book_label} contrasts it with {other_label}",
            "opposed_to": f"It is opposed to {other_label}",
            "relative_to": f"It is relative to {other_label}",
        }
    else:
        templates = {
            "has_deficiency": f"It appears as the deficiency of {other_label}",
            "has_excess": f"It appears as the excess of {other_label}",
            "concerns": f"It names the field for {other_label}",
            "is_a": f"It is a broader category for {other_label}",
            "determined_by": f"It helps determine {other_label}",
            "contrasted_with": f"{dataset.profile.book_label} contrasts {other_label} with it",
            "opposed_to": f"It stands opposed to {other_label}",
            "requires": f"{other_label} requires it",
            "formed_by": f"{other_label} is formed by it",
            "relative_to": f"{other_label} is relative to it",
        }
    return templates.get(
        relation.relation_type,
        (
            f"{dataset.concept_index[relation.source_id].primary_label} "
            f"{relation.relation_type.replace('_', ' ')} "
            f"{dataset.concept_index[relation.target_id].primary_label}"
        ),
    )


def relation_rows(
    relations: list[RelationAnnotation],
    dataset: ViewerDataset,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for relation in relations:
        rows.append(
            {
                "relation_type": relation.relation_type,
                "source": dataset.concept_index[relation.source_id].primary_label,
                "target": dataset.concept_index[relation.target_id].primary_label,
                "assertion_tier": relation.assertion_tier,
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
            "kind": concept.kind,
            "assertion_tier": concept.assertion_tier,
            "sections": ", ".join(str(section) for section in concept.sections),
        }
        for concept in concepts
    ]


def evidence_rows(
    concept: ConceptAnnotation,
    dataset: ViewerDataset,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for evidence in concept.evidence:
        passage = dataset.passage_index[evidence.passage_id]
        rows.append(
            {
                "citation": passage.citation_label,
                "passage_id": evidence.passage_id,
                "support_type": evidence.support_type,
                "note": evidence.note,
                "quote_excerpt": evidence.quote_excerpt or "",
            }
        )
    return rows


def passage_relation_rows(
    relations: tuple[RelationAnnotation, ...],
    dataset: ViewerDataset,
) -> list[dict[str, str]]:
    return [
        {
            "relation_type": relation.relation_type,
            "source": dataset.concept_index[relation.source_id].primary_label,
            "target": dataset.concept_index[relation.target_id].primary_label,
            "assertion_tier": relation.assertion_tier,
        }
        for relation in relations
    ]


def concept_detail_rows(concept: ConceptAnnotation) -> list[dict[str, str]]:
    return [
        {"field": "id", "value": concept.id},
        {"field": "kind", "value": concept.kind},
        {"field": "assertion tier", "value": concept.assertion_tier},
        {"field": "sections", "value": ", ".join(str(section) for section in concept.sections)},
        {"field": "source labels", "value": ", ".join(concept.source_labels)},
        {"field": "aliases", "value": ", ".join(concept.aliases) if concept.aliases else "None"},
    ]


def passage_preview(text: str, *, limit: int = 220) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


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


def edge_font_options(*, is_overall_map: bool) -> dict[str, Any]:
    return {
        "size": 10 if is_overall_map else 11,
        "align": "horizontal",
        "face": "Georgia, serif",
        "strokeWidth": 0,
        "color": "#223047",
        "background": "rgba(255, 250, 241, 0.96)",
        "vadjust": -10 if is_overall_map else -6,
    }


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
                "roundness": 0.28 if is_overall_map else 0.18,
            },
            "font": edge_font_options(is_overall_map=is_overall_map),
            "labelHighlightBold": False,
            "widthConstraint": {"maximum": 76 if is_overall_map else 92},
        },
    }
    network.set_options(json.dumps(options))
    return str(network.generate_html())
