from __future__ import annotations

from aristotle_graph.schemas import NormalizedBook, PassageRecord
from aristotle_graph.utils.hashing import stable_sha256


def _roman_book_number(book_number: int) -> str:
    remaining = book_number
    numerals = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    parts: list[str] = []
    for value, numeral in numerals:
        while remaining >= value:
            parts.append(numeral)
            remaining -= value
    return "".join(parts)


def segment_book(book: NormalizedBook) -> list[PassageRecord]:
    passages: list[PassageRecord] = []
    sequence_in_book = 1
    book_label = _roman_book_number(book.book_number)

    for section in sorted(book.sections, key=lambda item: item.section_number):
        source_url = book.source_url
        if section.source_anchor:
            source_url = f"{source_url}#{section.source_anchor}"

        for paragraph_index, paragraph in enumerate(section.paragraphs, start=1):
            passage_id = f"ne.b{book.book_number}.s{section.section_number}.p{paragraph_index}"
            passages.append(
                PassageRecord(
                    passage_id=passage_id,
                    work_id="nicomachean-ethics",
                    book_number=book.book_number,
                    chapter_or_section=f"part-{section.section_number}",
                    sequence_in_book=sequence_in_book,
                    source_id=book.source_id,
                    source_url=source_url,
                    citation_label=(
                        f"NE {book_label}.{section.section_number} \u00b6{paragraph_index}"
                    ),
                    text=paragraph,
                    char_count=len(paragraph),
                    hash=stable_sha256(paragraph),
                )
            )
            sequence_in_book += 1

    seen_ids = {passage.passage_id for passage in passages}
    if len(seen_ids) != len(passages):
        msg = "Passage IDs must be unique"
        raise ValueError(msg)

    return passages
