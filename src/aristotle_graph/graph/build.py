from __future__ import annotations

import json
from collections import Counter
from typing import Any

import networkx as nx

from aristotle_graph.annotations.validate import ValidatedAnnotationBundle
from aristotle_graph.schemas import PassageRecord


def _flatten_graphml_value(value: Any) -> str | int | float | bool:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _evidence_payload(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "evidence_count": len(records),
        "evidence_passage_ids_json": [record["passage_id"] for record in records],
        "evidence_notes_json": [record["note"] for record in records],
        "evidence_support_types_json": [record["support_type"] for record in records],
    }


def _passage_attrs(passage: PassageRecord) -> dict[str, Any]:
    return passage.model_dump(mode="json")


def _bundle_book_number(bundle: ValidatedAnnotationBundle) -> int:
    if bundle.passages:
        return bundle.passages[0].book_number
    if bundle.concepts:
        return bundle.concepts[0].book
    msg = "Cannot infer book number from an empty validated annotation bundle"
    raise ValueError(msg)


def build_graph_payload(bundle: ValidatedAnnotationBundle) -> dict[str, Any]:
    book_number = _bundle_book_number(bundle)
    return {
        "meta": {
            "book": book_number,
            "mode": bundle.mode,
            "concept_count": len(bundle.concepts),
            "relation_count": len(bundle.relations),
            "passage_count": len(bundle.passages),
            "passage_authority": f"data/interim/book{book_number}_passages.jsonl",
        },
        "nodes": [concept.model_dump(mode="json") for concept in bundle.concepts],
        "edges": [relation.model_dump(mode="json") for relation in bundle.relations],
        "passages": [passage.model_dump(mode="json") for passage in bundle.passages],
    }


def build_stats_payload(bundle: ValidatedAnnotationBundle) -> dict[str, Any]:
    book_number = _bundle_book_number(bundle)
    return {
        "book": book_number,
        "mode": bundle.mode,
        "concept_count": len(bundle.concepts),
        "relation_count": len(bundle.relations),
        "passage_count": len(bundle.passages),
        "concept_kinds": dict(
            sorted(Counter(concept.kind for concept in bundle.concepts).items())
        ),
        "relation_types": dict(
            sorted(Counter(relation.relation_type for relation in bundle.relations).items())
        ),
        "assertion_tiers": dict(
            sorted(
                Counter(
                    [concept.assertion_tier for concept in bundle.concepts]
                    + [relation.assertion_tier for relation in bundle.relations]
                ).items()
            )
        ),
        "concept_review_statuses": dict(
            sorted(Counter(concept.review_status for concept in bundle.concepts).items())
        ),
        "relation_review_statuses": dict(
            sorted(Counter(relation.review_status for relation in bundle.relations).items())
        ),
    }


def build_graphml_graph(bundle: ValidatedAnnotationBundle) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph(book=_bundle_book_number(bundle), mode=bundle.mode)

    for concept in bundle.concepts:
        concept_payload = concept.model_dump(mode="json")
        graph.add_node(
            concept.id,
            **{
                key: _flatten_graphml_value(value)
                for key, value in {
                    **concept_payload,
                    "label": concept.primary_label,
                    **_evidence_payload(concept_payload["evidence"]),
                }.items()
            },
        )

    for relation in bundle.relations:
        relation_payload = relation.model_dump(mode="json")
        graph.add_edge(
            relation.source_id,
            relation.target_id,
            key=relation.id,
            **{
                key: _flatten_graphml_value(value)
                for key, value in {
                    **relation_payload,
                    **_evidence_payload(relation_payload["evidence"]),
                }.items()
            },
        )

    return graph
