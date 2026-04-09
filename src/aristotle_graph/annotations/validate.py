from __future__ import annotations

from dataclasses import dataclass

from aristotle_graph.annotations.load import AnnotationBundle
from aristotle_graph.annotations.models import (
    ConceptAnnotation,
    RelationAnnotation,
    passage_section_number,
)
from aristotle_graph.schemas import PassageRecord


class AnnotationValidationError(ValueError):
    """Raised when annotations fail semantic validation."""

    def __init__(self, errors: list[str]):
        super().__init__("\n".join(errors))
        self.errors = errors


@dataclass(frozen=True)
class ValidatedAnnotationBundle:
    concepts: tuple[ConceptAnnotation, ...]
    relations: tuple[RelationAnnotation, ...]
    passages: tuple[PassageRecord, ...]
    mode: str
def validate_annotation_bundle(
    bundle: AnnotationBundle,
    passages: tuple[PassageRecord, ...],
    *,
    strict_approved: bool = False,
) -> ValidatedAnnotationBundle:
    errors: list[str] = []

    passage_index = {passage.passage_id: passage for passage in passages}
    concept_index: dict[str, ConceptAnnotation] = {}
    relation_index: dict[str, RelationAnnotation] = {}

    for concept in bundle.concepts:
        if concept.id in concept_index:
            errors.append(f"duplicate concept id: {concept.id}")
        concept_index[concept.id] = concept

    for relation in bundle.relations:
        if relation.id in relation_index:
            errors.append(f"duplicate relation id: {relation.id}")
        relation_index[relation.id] = relation

    for concept in bundle.concepts:
        for evidence in concept.evidence:
            passage = passage_index.get(evidence.passage_id)
            if passage is None:
                errors.append(
                    f"concept {concept.id} references missing passage {evidence.passage_id}"
                )
                continue
            if passage.book_number != concept.book:
                errors.append(
                    f"concept {concept.id} evidence passage {evidence.passage_id} is not in book "
                    f"{concept.book}"
                )
            section_number = passage_section_number(evidence.passage_id)
            if section_number not in concept.sections:
                errors.append(
                    f"concept {concept.id} evidence passage {evidence.passage_id} "
                    f"is not covered by sections {concept.sections}"
                )

    for relation in bundle.relations:
        if relation.source_id not in concept_index:
            errors.append(
                f"relation {relation.id} references missing source concept {relation.source_id}"
            )
        if relation.target_id not in concept_index:
            errors.append(
                f"relation {relation.id} references missing target concept {relation.target_id}"
            )
        for evidence in relation.evidence:
            if evidence.passage_id not in passage_index:
                errors.append(
                    f"relation {relation.id} references missing passage {evidence.passage_id}"
                )

    if strict_approved:
        export_concepts = sorted(
            [concept for concept in bundle.concepts if concept.review_status == "approved"],
            key=lambda concept: concept.id,
        )
        export_relations = sorted(
            [relation for relation in bundle.relations if relation.review_status == "approved"],
            key=lambda relation: relation.id,
        )
        approved_ids = {concept.id for concept in export_concepts}
        for relation in export_relations:
            if relation.source_id not in approved_ids or relation.target_id not in approved_ids:
                errors.append(
                    f"approved relation {relation.id} must only reference approved concepts"
                )
        mode = "strict_approved"
    else:
        export_concepts = sorted(bundle.concepts, key=lambda concept: concept.id)
        export_relations = sorted(bundle.relations, key=lambda relation: relation.id)
        mode = "candidate"

    if errors:
        raise AnnotationValidationError(errors)

    export_passages = tuple(
        sorted(passages, key=lambda row: row.sequence_in_book)
    )

    return ValidatedAnnotationBundle(
        concepts=tuple(export_concepts),
        relations=tuple(export_relations),
        passages=export_passages,
        mode=mode,
    )
