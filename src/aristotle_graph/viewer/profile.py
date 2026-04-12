from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ViewerProfile:
    slug: str
    app_title: str
    book_label: str
    default_concept_id: str
    start_here_concept_ids: tuple[str, ...]
    home_concept_ids: tuple[str, ...]
    home_passage_id: str
    concepts_filename: str
    relations_filename: str
    passages_filename: str
    graph_filename: str
    graphml_filename: str
    stats_filename: str


BOOK2_VIEWER_PROFILE = ViewerProfile(
    slug="book2",
    app_title="Aristotle Virtue Graph",
    book_label="Book II",
    default_concept_id="courage",
    start_here_concept_ids=(
        "courage",
        "temperance",
        "liberality",
        "truthfulness",
        "moral-virtue",
    ),
    home_concept_ids=(
        "courage",
        "moral-virtue",
        "habituation",
    ),
    home_passage_id="ne.b2.s7.p1",
    concepts_filename="book2_concepts.jsonl",
    relations_filename="book2_relations.jsonl",
    passages_filename="book2_passages.jsonl",
    graph_filename="book2_graph.json",
    graphml_filename="book2_graph.graphml",
    stats_filename="book2_stats.json",
)


PUBLIC_VIEWER_PROFILE = BOOK2_VIEWER_PROFILE
