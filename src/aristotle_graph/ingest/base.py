from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import httpx

from aristotle_graph.config import get_settings
from aristotle_graph.schemas import NormalizedBook
from aristotle_graph.source_registry import get_source


@dataclass(frozen=True)
class FetchedBook:
    source_id: str
    book_number: int
    source_url: str
    raw_text: str


class SourceAdapter(ABC):
    source_id: str

    @abstractmethod
    def default_book_url(self, book_number: int) -> str:
        """Return the default source URL for a book."""

    @abstractmethod
    def parse_book(self, raw_html: str, *, book_number: int) -> NormalizedBook:
        """Parse raw source content into normalized sections."""

    def fetch_book(self, book_number: int, *, input_file: Path | None = None) -> FetchedBook:
        if input_file is not None:
            return FetchedBook(
                source_id=self.source_id,
                book_number=book_number,
                source_url=str(input_file.resolve()),
                raw_text=input_file.read_text(encoding="utf-8"),
            )

        settings = get_settings()
        source_url = self.default_book_url(book_number)
        response = httpx.get(
            source_url,
            headers={"User-Agent": settings.user_agent},
            follow_redirects=True,
            timeout=settings.timeout_seconds,
        )
        response.raise_for_status()
        return FetchedBook(
            source_id=self.source_id,
            book_number=book_number,
            source_url=source_url,
            raw_text=response.text,
        )

    def source_metadata_url(self) -> str:
        return get_source(self.source_id).url
