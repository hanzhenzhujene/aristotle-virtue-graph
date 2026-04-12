from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SupportType = Literal["direct", "paraphrase", "editorial"]
AssertionTier = Literal["textual", "editorial_normalization", "interpretive"]
ReviewStatus = Literal["candidate", "approved"]
ConceptKind = Literal[
    "virtue",
    "vice",
    "domain",
    "principle",
    "state",
    "faculty",
    "passion",
    "process",
    "action",
    "person",
    "condition",
]
RelationType = Literal[
    "is_a",
    "formed_by",
    "concerns",
    "requires",
    "determined_by",
    "relative_to",
    "has_excess",
    "has_deficiency",
    "opposed_to",
    "contrasted_with",
]

_CONCEPT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_RELATION_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*(?:--[a-z0-9][a-z0-9_-]*){2}$")
_PASSAGE_ID_RE = re.compile(r"^ne\.b2\.s([1-9])\.p([1-9][0-9]*)$")


def make_relation_id(source_id: str, relation_type: RelationType, target_id: str) -> str:
    return f"{source_id}--{relation_type.replace('_', '-')}--{target_id}"


def passage_section_number(passage_id: str) -> int:
    match = _PASSAGE_ID_RE.fullmatch(passage_id)
    if match is None:
        msg = f"Unsupported passage_id format: {passage_id}"
        raise ValueError(msg)
    return int(match.group(1))


def _validate_non_empty_strings(values: list[str], *, field_name: str) -> list[str]:
    cleaned = [value.strip() for value in values]
    if any(not value for value in cleaned):
        msg = f"{field_name} must not contain blank strings"
        raise ValueError(msg)
    if len(set(cleaned)) != len(cleaned):
        msg = f"{field_name} must not contain duplicates"
        raise ValueError(msg)
    return cleaned


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passage_id: str
    support_type: SupportType
    note: str = Field(min_length=1, max_length=280)
    quote_excerpt: str | None = Field(default=None, max_length=280)

    @field_validator("passage_id")
    @classmethod
    def validate_passage_id(cls, value: str) -> str:
        if _PASSAGE_ID_RE.fullmatch(value) is None:
            msg = "passage_id must match the Book II passage export id format"
            raise ValueError(msg)
        return value

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "note must not be blank"
            raise ValueError(msg)
        return stripped

    @field_validator("quote_excerpt")
    @classmethod
    def validate_quote_excerpt(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            msg = "quote_excerpt must not be blank"
            raise ValueError(msg)
        return stripped


class ConceptAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    primary_label: str = Field(min_length=1, max_length=120)
    source_labels: list[str] = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    kind: ConceptKind
    description: str = Field(min_length=1, max_length=240)
    assertion_tier: AssertionTier
    book: Literal[2]
    sections: list[int] = Field(min_length=1)
    evidence: list[EvidenceRecord] = Field(min_length=1)
    review_status: ReviewStatus
    notes: str | None = Field(default=None, max_length=400)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if _CONCEPT_ID_RE.fullmatch(value) is None:
            msg = "concept ids must be ASCII kebab-case"
            raise ValueError(msg)
        return value

    @field_validator("primary_label", "description", "notes")
    @classmethod
    def validate_text_fields(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            msg = "text fields must not be blank"
            raise ValueError(msg)
        return stripped

    @field_validator("source_labels", "aliases")
    @classmethod
    def validate_label_lists(cls, value: list[str], info: object) -> list[str]:
        field_name = getattr(info, "field_name", "labels")
        return _validate_non_empty_strings(value, field_name=field_name)

    @field_validator("sections")
    @classmethod
    def validate_sections(cls, value: list[int]) -> list[int]:
        if any(section < 1 or section > 9 for section in value):
            msg = "sections must stay within Book II sections 1-9"
            raise ValueError(msg)
        if value != sorted(value):
            msg = "sections must be sorted"
            raise ValueError(msg)
        if len(set(value)) != len(value):
            msg = "sections must not contain duplicates"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_evidence_sections(self) -> ConceptAnnotation:
        evidence_sections = {passage_section_number(item.passage_id) for item in self.evidence}
        if not evidence_sections.issubset(set(self.sections)):
            msg = "all evidence passage sections must be listed in sections"
            raise ValueError(msg)
        return self


class RelationAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source_id: str
    relation_type: RelationType
    target_id: str
    assertion_tier: AssertionTier
    evidence: list[EvidenceRecord] = Field(min_length=1)
    review_status: ReviewStatus
    notes: str | None = Field(default=None, max_length=400)

    @field_validator("id", "source_id", "target_id", "notes")
    @classmethod
    def validate_text_ids(cls, value: str | None, info: object) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            msg = "text ids and notes must not be blank"
            raise ValueError(msg)
        field_name = getattr(info, "field_name", "")
        if field_name in {"source_id", "target_id"} and _CONCEPT_ID_RE.fullmatch(stripped) is None:
            msg = f"{field_name} must be an ASCII kebab-case concept id"
            raise ValueError(msg)
        if field_name == "id" and _RELATION_ID_RE.fullmatch(stripped) is None:
            msg = "relation ids must use the stable source--relation--target form"
            raise ValueError(msg)
        return stripped

    @model_validator(mode="after")
    def validate_relation_shape(self) -> RelationAnnotation:
        if self.source_id == self.target_id:
            msg = "relations must not be self-referential in Milestone 2"
            raise ValueError(msg)
        expected_id = make_relation_id(self.source_id, self.relation_type, self.target_id)
        if self.id != expected_id:
            msg = f"relation id must equal {expected_id}"
            raise ValueError(msg)
        return self
