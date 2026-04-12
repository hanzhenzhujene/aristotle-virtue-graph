from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from aristotle_graph.ingest.base import SourceAdapter
from aristotle_graph.ingest.normalize import build_normalized_book
from aristotle_graph.schemas import NormalizedBook
from aristotle_graph.source_registry import source_url_for_book


class WikisourceAdapter(SourceAdapter):
    source_id = "wikisource_ross_1908"

    def default_book_url(self, book_number: int) -> str:
        return source_url_for_book(self.source_id, book_number)

    def parse_book(self, raw_html: str, *, book_number: int) -> NormalizedBook:
        soup = BeautifulSoup(raw_html, "lxml")
        content = soup.select_one("#mw-content-text .mw-parser-output")
        if content is None:
            msg = f"Could not find Wikisource content container for Book {book_number}"
            raise ValueError(msg)

        sections: list[tuple[str, str | None, list[str]]] = []
        current_label: str | None = None
        current_anchor: str | None = None
        current_paragraphs: list[str] = []

        for child in content.children:
            if not isinstance(child, Tag):
                continue

            heading = child.select_one("h2")
            if heading is not None:
                label = heading.get_text(" ", strip=True)
                if not label.startswith("Part "):
                    continue
                if current_label is not None:
                    sections.append((current_label, current_anchor, current_paragraphs))
                current_label = label
                raw_anchor = heading.get("id")
                if isinstance(raw_anchor, list):
                    current_anchor = raw_anchor[0] if raw_anchor else None
                else:
                    current_anchor = raw_anchor
                current_paragraphs = []
                continue

            if child.name == "p" and current_label is not None:
                paragraph = child.get_text(" ", strip=True)
                if paragraph:
                    current_paragraphs.append(paragraph)

        if current_label is not None:
            sections.append((current_label, current_anchor, current_paragraphs))

        if not sections:
            msg = f"No Book {book_number} sections were parsed from Wikisource"
            raise ValueError(msg)

        return build_normalized_book(
            source_id=self.source_id,
            source_url=self.default_book_url(book_number),
            book_number=book_number,
            sections=sections,
        )
