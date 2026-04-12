from __future__ import annotations

import pytest

from aristotle_graph.source_registry import (
    get_source,
    list_sources,
    source_url_for_book,
    supported_books,
)


def test_source_registry_contains_expected_sources() -> None:
    sources = {source.source_id: source for source in list_sources()}

    assert "wikisource_ross_1908" in sources
    assert "mit_archive_ross" in sources
    assert sources["mit_archive_ross"].can_commit_raw_text is False
    assert supported_books("wikisource_ross_1908") == (2, 3)
    assert supported_books("mit_archive_ross") == (2, 3)
    assert "oldid" in source_url_for_book("wikisource_ross_1908", 2)
    assert "Book_Three" in source_url_for_book("wikisource_ross_1908", 3)


def test_get_source_returns_metadata() -> None:
    source = get_source("wikisource_ross_1908")

    assert source.translator == "W. D. Ross"


def test_source_url_for_book_rejects_unsupported_book() -> None:
    with pytest.raises(ValueError, match="does not support Book 6"):
        source_url_for_book("wikisource_ross_1908", 6)
