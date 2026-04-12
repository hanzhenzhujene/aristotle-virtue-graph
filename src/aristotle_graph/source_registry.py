from __future__ import annotations

from aristotle_graph.schemas import SourceRecord

WIKISOURCE_BOOK_URLS: dict[int, str] = {
    2: (
        "https://en.wikisource.org/w/index.php?title="
        "Nicomachean_Ethics_(Ross)/Book_Two&oldid=11905514"
    ),
    3: (
        "https://en.wikisource.org/w/index.php?title="
        "Nicomachean_Ethics_(Ross)/Book_Three&oldid=14820856"
    ),
}
MIT_BOOK_URLS: dict[int, str] = {
    2: "https://classics.mit.edu/Aristotle/nicomachaen.2.ii.html",
    3: "https://classics.mit.edu/Aristotle/nicomachaen.3.iii.html",
}

_SOURCE_BOOK_URLS: dict[str, dict[int, str]] = {
    "wikisource_ross_1908": WIKISOURCE_BOOK_URLS,
    "mit_archive_ross": MIT_BOOK_URLS,
}

_SOURCES: tuple[SourceRecord, ...] = (
    SourceRecord(
        source_id="wikisource_ross_1908",
        label="Wikisource Ross translation (pinned book-specific oldid URLs)",
        url=WIKISOURCE_BOOK_URLS[2],
        translator="W. D. Ross",
        publication_year=1908,
        license_status="public_domain_translation_hosted_on_wikisource",
        can_commit_raw_text=False,
        notes=(
            "Preferred canonical ingest target for the current Ethics books in scope. "
            "The translation is public-domain, but raw HTML remains local until the repo "
            "promotes a clearly redistributable raw-text representation. Runtime URL "
            "resolution uses pinned book-specific oldid links."
        ),
    ),
    SourceRecord(
        source_id="mit_archive_ross",
        label="MIT Internet Classics Archive Ross translation (book-specific URLs)",
        url=MIT_BOOK_URLS[2],
        translator="W. D. Ross",
        publication_year=1908,
        license_status="site_presentation_copyrighted",
        can_commit_raw_text=False,
        notes=(
            "Verification source only; do not treat as the committed canonical raw corpus. "
            "Runtime URL resolution uses book-specific MIT pages."
        ),
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


def supported_books(source_id: str) -> tuple[int, ...]:
    try:
        book_urls = _SOURCE_BOOK_URLS[source_id]
    except KeyError as exc:
        msg = f"Unknown source_id: {source_id}"
        raise KeyError(msg) from exc
    return tuple(sorted(book_urls))


def source_url_for_book(source_id: str, book_number: int) -> str:
    try:
        book_urls = _SOURCE_BOOK_URLS[source_id]
    except KeyError as exc:
        msg = f"Unknown source_id: {source_id}"
        raise KeyError(msg) from exc
    try:
        return book_urls[book_number]
    except KeyError as exc:
        supported = ", ".join(str(book) for book in sorted(book_urls))
        msg = (
            f"Source {source_id} does not support Book {book_number}; "
            f"supported books: {supported}"
        )
        raise ValueError(msg) from exc
