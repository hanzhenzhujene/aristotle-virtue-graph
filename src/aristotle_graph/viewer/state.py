from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from aristotle_graph.annotations.models import ConceptAnnotation, EvidenceRecord, RelationAnnotation
from aristotle_graph.schemas import PassageRecord
from aristotle_graph.viewer.load import ViewerDataset

VIEW_NAMES = (
    "Home",
    "Concept Explorer",
    "Passage Explorer",
    "Overall Map",
    "Stats",
)

START_HERE_IDS = (
    "courage",
    "temperance",
    "liberality",
    "truthfulness",
    "moral-virtue",
)

HOME_CONCEPT_IDS = (
    "courage",
    "habituation",
    "moral-virtue",
)

HOME_PASSAGE_ID = "ne.b2.s7.p1"

RELATION_PRIORITY = {
    "is_a": 0,
    "formed_by": 1,
    "requires": 2,
    "determined_by": 3,
    "relative_to": 4,
    "concerns": 5,
    "has_deficiency": 6,
    "has_excess": 7,
    "opposed_to": 8,
    "contrasted_with": 9,
}


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
    visible_concepts: Sequence[ConceptAnnotation],
) -> str | None:
    if not visible_concepts:
        return None
    for concept in visible_concepts:
        if concept.id == "courage":
            return concept.id
    return visible_concepts[0].id


def start_here_concept_ids(dataset: ViewerDataset) -> list[str]:
    return [
        concept_id for concept_id in START_HERE_IDS if concept_id in dataset.concept_index
    ]


def home_concept_ids(dataset: ViewerDataset) -> list[str]:
    return [concept_id for concept_id in HOME_CONCEPT_IDS if concept_id in dataset.concept_index]


def home_passage_id(dataset: ViewerDataset) -> str | None:
    if HOME_PASSAGE_ID in dataset.passage_index:
        return HOME_PASSAGE_ID
    if dataset.passages:
        return dataset.passages[0].passage_id
    return None


def evidence_passage_ids(evidence_records: Sequence[EvidenceRecord]) -> list[str]:
    ordered_ids: list[str] = []
    seen: set[str] = set()
    for evidence in evidence_records:
        if evidence.passage_id in seen:
            continue
        seen.add(evidence.passage_id)
        ordered_ids.append(evidence.passage_id)
    return ordered_ids


def passage_options(
    dataset: ViewerDataset,
    visible_passages: list[PassageRecord],
    *,
    focused_passage_id: str | None = None,
) -> list[PassageRecord]:
    if focused_passage_id is None or focused_passage_id not in dataset.passage_index:
        return visible_passages

    visible_ids = {passage.passage_id for passage in visible_passages}
    if focused_passage_id in visible_ids:
        return visible_passages

    focused_passage = dataset.passage_index[focused_passage_id]
    return [focused_passage, *visible_passages]


def passage_navigation_targets(
    visible_passages: Sequence[PassageRecord],
    selected_passage_id: str | None,
) -> tuple[str | None, str | None]:
    if selected_passage_id is None:
        return (None, None)
    ordered_ids = [passage.passage_id for passage in visible_passages]
    if selected_passage_id not in ordered_ids:
        return (None, None)
    index = ordered_ids.index(selected_passage_id)
    previous_id = ordered_ids[index - 1] if index > 0 else None
    next_id = ordered_ids[index + 1] if index < len(ordered_ids) - 1 else None
    return (previous_id, next_id)


def _section_summary(sections: frozenset[int]) -> str:
    if not sections or sections == frozenset(range(1, 10)):
        return "Sections 1–9"
    ordered_sections = sorted(sections)
    if len(ordered_sections) == 1:
        return f"Section {ordered_sections[0]}"
    return "Sections " + ", ".join(str(section) for section in ordered_sections)


def filter_summary_text(dataset: ViewerDataset, filters: ViewerFilters) -> str:
    all_kinds = set(available_concept_kinds(dataset))
    all_relations = set(available_relation_types(dataset))
    concept_summary = (
        "All concepts"
        if not filters.concept_kinds or set(filters.concept_kinds) == all_kinds
        else f"{len(filters.concept_kinds)} concept kinds"
    )
    relation_summary = (
        "All relations"
        if not filters.relation_types or set(filters.relation_types) == all_relations
        else f"{len(filters.relation_types)} relation types"
    )
    pieces = [concept_summary, relation_summary, _section_summary(filters.sections)]
    search_text = filters.search_text.strip()
    if search_text:
        pieces.insert(0, f"Search: {search_text}")
    return " · ".join(pieces)


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


def build_filtered_graph(
    dataset: ViewerDataset,
    filters: ViewerFilters,
    *,
    include_isolates: bool = True,
) -> tuple[list[ConceptAnnotation], list[RelationAnnotation]]:
    visible_concepts = filter_concepts(dataset, filters)
    visible_concept_ids = {concept.id for concept in visible_concepts}
    visible_relations = [
        relation
        for relation in filter_relations(dataset, filters)
        if relation.source_id in visible_concept_ids and relation.target_id in visible_concept_ids
    ]

    if include_isolates:
        return (visible_concepts, visible_relations)

    connected_ids = {
        concept_id
        for relation in visible_relations
        for concept_id in (relation.source_id, relation.target_id)
    }
    connected_concepts = [
        concept for concept in visible_concepts if concept.id in connected_ids
    ]
    return (connected_concepts, visible_relations)


def graph_degree_rows(
    concepts: Sequence[ConceptAnnotation],
    relations: Sequence[RelationAnnotation],
) -> list[dict[str, object]]:
    in_degree: Counter[str] = Counter()
    out_degree: Counter[str] = Counter()

    for relation in relations:
        out_degree[relation.source_id] += 1
        in_degree[relation.target_id] += 1

    rows = [
        {
            "label": concept.primary_label,
            "id": concept.id,
            "kind": concept.kind,
            "in_degree": in_degree[concept.id],
            "out_degree": out_degree[concept.id],
            "total_degree": in_degree[concept.id] + out_degree[concept.id],
        }
        for concept in concepts
    ]
    rows.sort(
        key=lambda row: (
            -cast(int, row["total_degree"]),
            -cast(int, row["out_degree"]),
            cast(str, row["label"]).lower(),
        )
    )
    return rows


def relation_sort_key(
    relation: RelationAnnotation,
    dataset: ViewerDataset,
    *,
    focal_concept_id: str,
) -> tuple[int, str, str]:
    other_concept_id = (
        relation.target_id if relation.source_id == focal_concept_id else relation.source_id
    )
    other_label = dataset.concept_index.get(other_concept_id)
    return (
        RELATION_PRIORITY.get(relation.relation_type, 99),
        other_label.primary_label.lower() if other_label is not None else other_concept_id,
        relation.id,
    )


def concept_stats(dataset: ViewerDataset) -> dict[str, int]:
    return dict(sorted(Counter(concept.kind for concept in dataset.concepts).items()))


def relation_stats(dataset: ViewerDataset) -> dict[str, int]:
    return dict(sorted(Counter(relation.relation_type for relation in dataset.relations).items()))
