from __future__ import annotations

from aristotle_graph.ingest.segment import segment_book
from aristotle_graph.schemas import NormalizedBook, NormalizedSection


def test_segmentation_produces_stable_passage_ids() -> None:
    book = NormalizedBook(
        book_number=2,
        source_id="wikisource_ross_1908",
        source_url="https://example.test/book-two",
        sections=[
            NormalizedSection(
                section_number=1,
                section_label="Part 1",
                source_anchor="Part_1",
                paragraphs=["Paragraph one.", "Paragraph two."],
            ),
            NormalizedSection(
                section_number=2,
                section_label="Part 2",
                source_anchor="Part_2",
                paragraphs=["Paragraph three."],
            ),
        ],
    )

    first_run = segment_book(book)
    second_run = segment_book(book)

    assert [passage.passage_id for passage in first_run] == [
        "ne.b2.s1.p1",
        "ne.b2.s1.p2",
        "ne.b2.s2.p1",
    ]
    assert [passage.passage_id for passage in first_run] == [
        passage.passage_id for passage in second_run
    ]
    assert first_run[0].source_url.endswith("#Part_1")
    assert first_run[-1].sequence_in_book == 3
