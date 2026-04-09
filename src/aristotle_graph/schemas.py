from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    label: str
    url: str
    translator: str
    publication_year: int
    license_status: str
    can_commit_raw_text: bool
    notes: str


class NormalizedSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_number: int
    section_label: str
    source_anchor: str | None = None
    paragraphs: list[str] = Field(default_factory=list)

    @field_validator("section_number")
    @classmethod
    def validate_section_number(cls, value: int) -> int:
        if value < 1:
            msg = "section_number must be positive"
            raise ValueError(msg)
        return value


class NormalizedBook(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_id: Literal["nicomachean-ethics"] = "nicomachean-ethics"
    book_number: int
    source_id: str
    source_url: str
    sections: list[NormalizedSection] = Field(default_factory=list)

    @field_validator("book_number")
    @classmethod
    def validate_book_number(cls, value: int) -> int:
        if value < 1:
            msg = "book_number must be positive"
            raise ValueError(msg)
        return value


class PassageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passage_id: str
    work_id: Literal["nicomachean-ethics"]
    book_number: int
    chapter_or_section: str
    sequence_in_book: int
    source_id: str
    source_url: str
    citation_label: str
    text: str
    cts_urn: str | None = None
    bekker_ref: str | None = None
    char_count: int
    hash: str

    @field_validator("book_number", "sequence_in_book")
    @classmethod
    def validate_positive_int(cls, value: int) -> int:
        if value < 1:
            msg = "value must be positive"
            raise ValueError(msg)
        return value
