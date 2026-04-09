from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from aristotle_graph.annotations.models import ConceptAnnotation, RelationAnnotation
from aristotle_graph.schemas import PassageRecord
from aristotle_graph.viewer.load import ViewerDataset


@dataclass(frozen=True)
class ViewerFilters:
    search_text: str = ""
    concept_kinds: frozenset[str] = frozenset()
    relation_types: frozenset[str] = frozenset()
    assertion_tiers: frozenset[str] = frozenset()
    sections: frozenset[int] = frozenset()


def available_concept_kinds(dataset: ViewerDataset) -> list[str]:
    return sorted({concept.kind for concept in dataset.concepts})


def available_relation_types(dataset: ViewerDataset) -> list[str]:
    return sorted({relation.relation_type for relation in dataset.relations})


def available_assertion_tiers(dataset: ViewerDataset) -> list[str]:
    return sorted(
        {
            concept.assertion_tier for concept in dataset.concepts
        }
        | {relation.assertion_tier for relation in dataset.relations}
    )


def _matches_sections(section_values: set[int], selected_sections: frozenset[int]) -> bool:
    return not selected_sections or bool(section_values & set(selected_sections))


def filter_concepts(dataset: ViewerDataset, filters: ViewerFilters) -> list[ConceptAnnotation]:
    search_text = filters.search_text.strip().lower()
    filtered: list[ConceptAnnotation] = []

    for concept in dataset.concepts:
        if filters.concept_kinds and concept.kind not in filters.concept_kinds:
            continue
        if filters.assertion_tiers and concept.assertion_tier not in filters.assertion_tiers:
            continue
        if not _matches_sections(set(concept.sections), filters.sections):
            continue

        haystack = " ".join(
            [
                concept.id,
                concept.primary_label,
                concept.description,
                *concept.source_labels,
                *concept.aliases,
            ]
        ).lower()
        if search_text and search_text not in haystack:
            continue
        filtered.append(concept)

    return filtered


def filter_relations(
    dataset: ViewerDataset,
    filters: ViewerFilters,
    *,
    related_to_concept_id: str | None = None,
) -> list[RelationAnnotation]:
    filtered: list[RelationAnnotation] = []
    selected_sections = set(filters.sections)

    for relation in dataset.relations:
        if filters.relation_types and relation.relation_type not in filters.relation_types:
            continue
        if filters.assertion_tiers and relation.assertion_tier not in filters.assertion_tiers:
            continue
        if related_to_concept_id is not None and related_to_concept_id not in {
            relation.source_id,
            relation.target_id,
        }:
            continue
        if selected_sections:
            passage_section_numbers = {
                int(evidence.passage_id.split(".")[2].removeprefix("s"))
                for evidence in relation.evidence
            }
            if not _matches_sections(passage_section_numbers, filters.sections):
                continue
        filtered.append(relation)

    return filtered


def filter_passages(
    dataset: ViewerDataset,
    filters: ViewerFilters,
) -> list[PassageRecord]:
    selected_sections = set(filters.sections)
    if not selected_sections:
        return list(dataset.passages)
    return [
        passage
        for passage in dataset.passages
        if int(passage.passage_id.split(".")[2].removeprefix("s")) in selected_sections
    ]


def default_concept_id(
    dataset: ViewerDataset,
    visible_concepts: list[ConceptAnnotation],
) -> str | None:
    if not visible_concepts:
        return None
    for concept in visible_concepts:
        if concept.id == "courage":
            return concept.id
    return visible_concepts[0].id


def build_ego_graph(
    dataset: ViewerDataset,
    center_concept_id: str,
    filters: ViewerFilters,
    *,
    hops: int,
) -> tuple[list[ConceptAnnotation], list[RelationAnnotation]]:
    if center_concept_id not in dataset.concept_index:
        return ([], [])

    allowed_relations = filter_relations(dataset, filters)
    relation_by_endpoint: dict[str, list[RelationAnnotation]] = {}
    for relation in allowed_relations:
        relation_by_endpoint.setdefault(relation.source_id, []).append(relation)
        relation_by_endpoint.setdefault(relation.target_id, []).append(relation)

    visited = {center_concept_id}
    frontier = {center_concept_id}
    for _ in range(max(1, hops)):
        next_frontier: set[str] = set()
        for concept_id in frontier:
            for relation in relation_by_endpoint.get(concept_id, []):
                next_frontier.add(relation.source_id)
                next_frontier.add(relation.target_id)
        next_frontier -= visited
        visited |= next_frontier
        frontier = next_frontier
        if not frontier:
            break

    visible_relations = [
        relation
        for relation in allowed_relations
        if relation.source_id in visited and relation.target_id in visited
    ]
    visible_nodes = sorted(
        [dataset.concept_index[concept_id] for concept_id in visited],
        key=lambda concept: concept.primary_label.lower(),
    )
    return (visible_nodes, visible_relations)


def concept_stats(dataset: ViewerDataset) -> dict[str, int]:
    return dict(sorted(Counter(concept.kind for concept in dataset.concepts).items()))


def relation_stats(dataset: ViewerDataset) -> dict[str, int]:
    return dict(sorted(Counter(relation.relation_type for relation in dataset.relations).items()))
