from __future__ import annotations

from pathlib import Path

from aristotle_graph.ingest.mit_archive import MITArchiveAdapter
from aristotle_graph.ingest.wikisource import WikisourceAdapter


def test_wikisource_adapter_parses_sections() -> None:
    raw_html = Path("tests/fixtures/wikisource_book2_excerpt.html").read_text(encoding="utf-8")

    normalized = WikisourceAdapter().parse_book(raw_html, book_number=2)

    assert len(normalized.sections) == 2
    assert normalized.sections[0].section_number == 1
    assert normalized.sections[0].paragraphs[0].startswith("Virtue, then")
    assert normalized.sections[1].source_anchor == "Part_2"


def test_mit_adapter_parses_sections() -> None:
    raw_html = Path("tests/fixtures/mit_book2_excerpt.html").read_text(encoding="utf-8")

    normalized = MITArchiveAdapter().parse_book(raw_html, book_number=2)

    assert len(normalized.sections) == 2
    assert normalized.sections[0].section_label == "Part 1"
    assert normalized.sections[1].paragraphs[0].startswith("Since, then")
