from __future__ import annotations

import re
from collections.abc import Sequence

from aristotle_graph.schemas import NormalizedBook, NormalizedSection
from aristotle_graph.utils.text import normalize_paragraph_text

_PART_RE = re.compile(r"Part\s+(\d+)", re.IGNORECASE)


def extract_section_number(label: str) -> int:
    match = _PART_RE.fullmatch(label.strip())
    if match is None:
        msg = f"Unsupported section label: {label}"
        raise ValueError(msg)
    return int(match.group(1))


def build_normalized_book(
    *,
    source_id: str,
    source_url: str,
    book_number: int,
    sections: Sequence[tuple[str, str | None, Sequence[str]]],
) -> NormalizedBook:
    normalized_sections: list[NormalizedSection] = []
    for label, anchor, paragraphs in sections:
        cleaned_paragraphs = [
            normalize_paragraph_text(paragraph) for paragraph in paragraphs if paragraph.strip()
        ]
        if not cleaned_paragraphs:
            continue
        normalized_sections.append(
            NormalizedSection(
                section_number=extract_section_number(label),
                section_label=label,
                source_anchor=anchor,
                paragraphs=cleaned_paragraphs,
            )
        )

    return NormalizedBook(
        book_number=book_number,
        source_id=source_id,
        source_url=source_url,
        sections=normalized_sections,
    )
