from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from aristotle_graph.annotations.validate import ValidatedAnnotationBundle
from aristotle_graph.config import get_settings
from aristotle_graph.graph.build import (
    build_graph_payload,
    build_graphml_graph,
    build_stats_payload,
)
from aristotle_graph.utils.io import ensure_parent_directory, write_json, write_jsonl


@dataclass(frozen=True)
class ExportPaths:
    passages_path: Path
    concepts_path: Path
    relations_path: Path
    graph_path: Path
    graphml_path: Path
    stats_path: Path


def default_export_paths(*, book: int = 2, output_dir: Path | None = None) -> ExportPaths:
    base_dir = output_dir or get_settings().processed_dir
    return ExportPaths(
        passages_path=base_dir / f"book{book}_passages.jsonl",
        concepts_path=base_dir / f"book{book}_concepts.jsonl",
        relations_path=base_dir / f"book{book}_relations.jsonl",
        graph_path=base_dir / f"book{book}_graph.json",
        graphml_path=base_dir / f"book{book}_graph.graphml",
        stats_path=base_dir / f"book{book}_stats.json",
    )


def export_passages(bundle: ValidatedAnnotationBundle, path: Path) -> Path:
    write_jsonl(path, [passage.model_dump(mode="json") for passage in bundle.passages])
    return path


def export_concepts(bundle: ValidatedAnnotationBundle, path: Path) -> Path:
    write_jsonl(path, [concept.model_dump(mode="json") for concept in bundle.concepts])
    return path


def export_relations(bundle: ValidatedAnnotationBundle, path: Path) -> Path:
    write_jsonl(path, [relation.model_dump(mode="json") for relation in bundle.relations])
    return path


def export_graph(bundle: ValidatedAnnotationBundle, path: Path) -> Path:
    write_json(path, build_graph_payload(bundle))
    return path


def export_graphml(bundle: ValidatedAnnotationBundle, path: Path) -> Path:
    ensure_parent_directory(path)
    nx.write_graphml(build_graphml_graph(bundle), path)
    return path


def export_stats(bundle: ValidatedAnnotationBundle, path: Path) -> Path:
    write_json(path, build_stats_payload(bundle))
    return path


def export_all(
    bundle: ValidatedAnnotationBundle,
    *,
    book: int = 2,
    output_dir: Path | None = None,
) -> ExportPaths:
    paths = default_export_paths(book=book, output_dir=output_dir)
    export_passages(bundle, paths.passages_path)
    export_concepts(bundle, paths.concepts_path)
    export_relations(bundle, paths.relations_path)
    export_graph(bundle, paths.graph_path)
    export_graphml(bundle, paths.graphml_path)
    export_stats(bundle, paths.stats_path)
    return paths
