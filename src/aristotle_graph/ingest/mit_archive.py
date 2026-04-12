from __future__ import annotations

import re
from html import unescape

from bs4 import BeautifulSoup, Tag

from aristotle_graph.ingest.base import SourceAdapter
from aristotle_graph.ingest.normalize import build_normalized_book
from aristotle_graph.schemas import NormalizedBook
from aristotle_graph.source_registry import MIT_BOOK_II_URL

_ANCHOR_RE = re.compile(r"<a[^>]+name=\"\d+\"[^>]*></a>", flags=re.IGNORECASE)
_SECTION_MARKER_RE = re.compile(
    r"(?:<br\s*/?>\s*){1,2}(\d+)\s*(?:<br\s*/?>\s*){2}",
    flags=re.IGNORECASE,
)
_BREAK_RE = re.compile(r"<br\s*/?>\s*<br\s*/?>", flags=re.IGNORECASE)
_SINGLE_BREAK_RE = re.compile(r"<br\s*/?>", flags=re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


class MITArchiveAdapter(SourceAdapter):
    source_id = "mit_archive_ross"

    def default_book_url(self, book_number: int) -> str:
        if book_number != 2:
            msg = "Milestone 1 only supports Nicomachean Ethics Book II"
            raise ValueError(msg)
        return MIT_BOOK_II_URL

    def parse_book(self, raw_html: str, *, book_number: int) -> NormalizedBook:
        soup = BeautifulSoup(raw_html, "lxml")
        start_anchor = soup.find("a", attrs={"name": "start"})
        if start_anchor is None:
            msg = "Could not find MIT Book II start anchor"
            raise ValueError(msg)

        fragment_parts: list[str] = []
        for sibling in start_anchor.next_siblings:
            if isinstance(sibling, Tag) and sibling.name == "hr":
                break
            fragment_parts.append(str(sibling))

        fragment = "".join(fragment_parts)
        fragment = _ANCHOR_RE.sub("", fragment)
        fragment = _SECTION_MARKER_RE.sub(r"\n\n\1\n\n", fragment)
        fragment = _BREAK_RE.sub("\n\n", fragment)
        fragment = _SINGLE_BREAK_RE.sub(" ", fragment)
        fragment = _TAG_RE.sub("", fragment)
        blocks = [unescape(block).strip() for block in fragment.split("\n\n") if block.strip()]

        sections: list[tuple[str, None, list[str]]] = []
        current_section: str | None = None
        current_paragraphs: list[str] = []

        for block in blocks:
            if block == "* * *":
                continue
            if block.isdigit():
                if current_section is not None:
                    sections.append((f"Part {current_section}", None, current_paragraphs))
                current_section = block
                current_paragraphs = []
                continue
            if current_section is not None:
                current_paragraphs.append(block)

        if current_section is not None:
            sections.append((f"Part {current_section}", None, current_paragraphs))

        if not sections:
            msg = "No Book II sections were parsed from MIT"
            raise ValueError(msg)

        return build_normalized_book(
            source_id=self.source_id,
            source_url=self.default_book_url(book_number),
            book_number=book_number,
            sections=sections,
        )
