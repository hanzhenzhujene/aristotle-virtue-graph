from __future__ import annotations

from aristotle_graph.source_registry import get_source, list_sources


def test_source_registry_contains_expected_sources() -> None:
    sources = {source.source_id: source for source in list_sources()}

    assert "wikisource_ross_1908" in sources
    assert "mit_archive_ross" in sources
    assert sources["mit_archive_ross"].can_commit_raw_text is False
    assert "oldid" in sources["wikisource_ross_1908"].url


def test_get_source_returns_metadata() -> None:
    source = get_source("wikisource_ross_1908")

    assert source.translator == "W. D. Ross"
