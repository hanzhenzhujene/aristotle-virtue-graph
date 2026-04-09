from __future__ import annotations

from aristotle_graph.schemas import SourceRecord

WIKISOURCE_BOOK_II_URL = (
    "https://en.wikisource.org/w/index.php?title="
    "Nicomachean_Ethics_(Ross)/Book_Two&oldid=11905514"
)
MIT_BOOK_II_URL = "https://classics.mit.edu/Aristotle/nicomachaen.2.ii.html"

_SOURCES: tuple[SourceRecord, ...] = (
    SourceRecord(
        source_id="wikisource_ross_1908",
        label="Wikisource Ross translation (Book II oldid 11905514)",
        url=WIKISOURCE_BOOK_II_URL,
        translator="W. D. Ross",
        publication_year=1908,
        license_status="public_domain_translation_hosted_on_wikisource",
        can_commit_raw_text=False,
        notes=(
            "Preferred canonical ingest target for Milestone 1. The translation is public-domain, "
            "but raw HTML remains local until the repo promotes a clearly redistributable raw-text "
            "representation."
        ),
    ),
    SourceRecord(
        source_id="mit_archive_ross",
        label="MIT Internet Classics Archive Ross translation (Book II)",
        url=MIT_BOOK_II_URL,
        translator="W. D. Ross",
        publication_year=1908,
        license_status="site_presentation_copyrighted",
        can_commit_raw_text=False,
        notes="Verification source only; do not treat as the committed canonical raw corpus.",
    ),
)


def list_sources() -> tuple[SourceRecord, ...]:
    return _SOURCES


def get_source(source_id: str) -> SourceRecord:
    for source in _SOURCES:
        if source.source_id == source_id:
            return source
    msg = f"Unknown source_id: {source_id}"
    raise KeyError(msg)
