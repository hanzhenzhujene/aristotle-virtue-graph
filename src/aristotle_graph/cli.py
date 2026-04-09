from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from aristotle_graph.annotations.export import (
    default_export_paths,
    export_all,
    export_concepts,
    export_graph,
    export_graphml,
    export_passages,
    export_relations,
    export_stats,
)
from aristotle_graph.annotations.load import (
    AnnotationLoadError,
    load_annotation_bundle,
    load_passage_authority,
)
from aristotle_graph.annotations.validate import (
    AnnotationValidationError,
    ValidatedAnnotationBundle,
    validate_annotation_bundle,
)
from aristotle_graph.config import ensure_project_directories, get_settings
from aristotle_graph.graph.build import build_stats_payload
from aristotle_graph.ingest.base import SourceAdapter
from aristotle_graph.ingest.mit_archive import MITArchiveAdapter
from aristotle_graph.ingest.segment import segment_book
from aristotle_graph.ingest.wikisource import WikisourceAdapter
from aristotle_graph.source_registry import get_source, list_sources
from aristotle_graph.utils.io import read_text, write_json, write_jsonl, write_text

app = typer.Typer(no_args_is_help=True)
sources_app = typer.Typer(no_args_is_help=True)
annotations_app = typer.Typer(no_args_is_help=True)
app.add_typer(sources_app, name="sources")
app.add_typer(annotations_app, name="annotations")

SourceOption = Annotated[str, typer.Option(..., help="Source identifier.")]
BookOption = Annotated[int, typer.Option(..., min=1, help="Book number to process.")]
InputFileOption = Annotated[
    Path | None,
    typer.Option(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Use a local source file instead of the network or cached raw file.",
    ),
]
OutputDirOption = Annotated[
    Path | None,
    typer.Option(
        file_okay=False,
        dir_okay=True,
        writable=True,
        help="Optional output directory for processed exports.",
    ),
]


def _validate_loaded_annotations(*, book: int, strict_approved: bool) -> ValidatedAnnotationBundle:
    try:
        bundle = load_annotation_bundle(book)
        passages = load_passage_authority(book)
        return validate_annotation_bundle(
            bundle,
            passages,
            strict_approved=strict_approved,
        )
    except AnnotationLoadError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except AnnotationValidationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


def _get_adapter(source_id: str) -> SourceAdapter:
    adapters: dict[str, SourceAdapter] = {
        "wikisource_ross_1908": WikisourceAdapter(),
        "mit_archive_ross": MITArchiveAdapter(),
    }
    try:
        return adapters[source_id]
    except KeyError as exc:
        msg = f"Unsupported source adapter: {source_id}"
        raise typer.BadParameter(msg) from exc


def _book_suffix(book_number: int) -> str:
    return f"book{book_number}"


def _default_raw_path(source_id: str, book_number: int) -> Path:
    return get_settings().raw_dir / source_id / f"{_book_suffix(book_number)}.html"


def _default_normalized_path(source_id: str, book_number: int) -> Path:
    filename = f"{_book_suffix(book_number)}_{source_id}_normalized.json"
    return get_settings().interim_dir / filename


def _default_passage_path(book_number: int) -> Path:
    return get_settings().interim_dir / f"{_book_suffix(book_number)}_passages.jsonl"


def _load_or_fetch_raw(
    *,
    adapter: SourceAdapter,
    source_id: str,
    book_number: int,
    input_file: Path | None,
) -> str:
    raw_path = _default_raw_path(source_id, book_number)
    if input_file is not None:
        return read_text(input_file)
    if raw_path.exists():
        return read_text(raw_path)
    fetched = adapter.fetch_book(book_number)
    write_text(raw_path, fetched.raw_text)
    return fetched.raw_text


@sources_app.command("list")
def list_sources_command() -> None:
    """List registered Book II sources."""

    for source in list_sources():
        typer.echo(
            f"{source.source_id}\n"
            f"  label: {source.label}\n"
            f"  url: {source.url}\n"
            f"  can_commit_raw_text: {source.can_commit_raw_text}\n"
            f"  notes: {source.notes}\n"
        )


@app.command()
def fetch(
    source: SourceOption,
    book: BookOption,
    input_file: InputFileOption = None,
) -> None:
    """Fetch raw source content for a book."""

    ensure_project_directories()
    adapter = _get_adapter(source)
    raw_path = _default_raw_path(source, book)
    if input_file is not None:
        write_text(raw_path, read_text(input_file))
    else:
        fetched = adapter.fetch_book(book)
        write_text(raw_path, fetched.raw_text)
    typer.echo(str(raw_path))


@app.command()
def normalize(
    source: SourceOption,
    book: BookOption,
    input_file: InputFileOption = None,
) -> None:
    """Normalize Book II source content into stable sections."""

    ensure_project_directories()
    adapter = _get_adapter(source)
    raw_html = _load_or_fetch_raw(
        adapter=adapter,
        source_id=source,
        book_number=book,
        input_file=input_file,
    )
    normalized = adapter.parse_book(raw_html, book_number=book)
    output_path = _default_normalized_path(source, book)
    write_json(output_path, normalized.model_dump(mode="json"))
    typer.echo(str(output_path))


@app.command()
def segment(
    source: SourceOption,
    book: BookOption,
    input_file: InputFileOption = None,
) -> None:
    """Write stable Book II passage records."""

    ensure_project_directories()
    adapter = _get_adapter(source)
    raw_html = _load_or_fetch_raw(
        adapter=adapter,
        source_id=source,
        book_number=book,
        input_file=input_file,
    )
    normalized = adapter.parse_book(raw_html, book_number=book)
    normalized_path = _default_normalized_path(source, book)
    write_json(normalized_path, normalized.model_dump(mode="json"))

    passages = segment_book(normalized)
    output_path = _default_passage_path(book)
    write_jsonl(output_path, [passage.model_dump(mode="json") for passage in passages])
    typer.echo(str(output_path))


@app.command()
def show_source(source: str = typer.Argument(..., help="Source identifier.")) -> None:
    """Show registered metadata for a source."""

    metadata = get_source(source)
    typer.echo(json.dumps(metadata.model_dump(mode="json"), ensure_ascii=False, indent=2))


@annotations_app.command("validate")
def validate_annotations(
    book: int = typer.Option(2, min=1, help="Book number to validate."),
    strict_approved: bool = typer.Option(
        False,
        "--strict-approved",
        help="Validate only the approved subset and require approved-only dependencies.",
    ),
) -> None:
    """Validate annotation files against schemas, passages, and cross-references."""

    validated = _validate_loaded_annotations(book=book, strict_approved=strict_approved)
    typer.echo(
        json.dumps(
            {
                "book": book,
                "mode": validated.mode,
                "concept_count": len(validated.concepts),
                "relation_count": len(validated.relations),
                "passage_count": len(validated.passages),
            },
            indent=2,
        )
    )


@annotations_app.command("export-concepts")
def export_annotation_concepts(
    book: int = typer.Option(2, min=1, help="Book number to export."),
    strict_approved: bool = typer.Option(
        False,
        "--strict-approved",
        help="Export only the approved subset.",
    ),
    output_dir: OutputDirOption = None,
) -> None:
    """Export processed concept rows."""

    validated = _validate_loaded_annotations(book=book, strict_approved=strict_approved)
    path = default_export_paths(book=book, output_dir=output_dir).concepts_path
    export_concepts(validated, path)
    typer.echo(str(path))


@annotations_app.command("export-passages")
def export_annotation_passages(
    book: int = typer.Option(2, min=1, help="Book number to export."),
    strict_approved: bool = typer.Option(
        False,
        "--strict-approved",
        help="Export the processed passages alongside the approved subset metadata.",
    ),
    output_dir: OutputDirOption = None,
) -> None:
    """Export processed passage rows."""

    validated = _validate_loaded_annotations(book=book, strict_approved=strict_approved)
    path = default_export_paths(book=book, output_dir=output_dir).passages_path
    export_passages(validated, path)
    typer.echo(str(path))


@annotations_app.command("export-relations")
def export_annotation_relations(
    book: int = typer.Option(2, min=1, help="Book number to export."),
    strict_approved: bool = typer.Option(
        False,
        "--strict-approved",
        help="Export only the approved subset.",
    ),
    output_dir: OutputDirOption = None,
) -> None:
    """Export processed relation rows."""

    validated = _validate_loaded_annotations(book=book, strict_approved=strict_approved)
    path = default_export_paths(book=book, output_dir=output_dir).relations_path
    export_relations(validated, path)
    typer.echo(str(path))


@annotations_app.command("build-graph")
def build_annotation_graph(
    book: int = typer.Option(2, min=1, help="Book number to export."),
    strict_approved: bool = typer.Option(
        False,
        "--strict-approved",
        help="Export only the approved subset.",
    ),
    output_dir: OutputDirOption = None,
) -> None:
    """Build the downstream graph JSON, GraphML, and stats payloads."""

    validated = _validate_loaded_annotations(book=book, strict_approved=strict_approved)
    paths = default_export_paths(book=book, output_dir=output_dir)
    export_graph(validated, paths.graph_path)
    export_graphml(validated, paths.graphml_path)
    export_stats(validated, paths.stats_path)
    typer.echo(str(paths.graph_path))
    typer.echo(str(paths.graphml_path))
    typer.echo(str(paths.stats_path))


@annotations_app.command("stats")
def annotation_stats(
    book: int = typer.Option(2, min=1, help="Book number to inspect."),
    strict_approved: bool = typer.Option(
        False,
        "--strict-approved",
        help="Report stats for the approved subset only.",
    ),
) -> None:
    """Print graph stats for the validated annotation bundle."""

    validated = _validate_loaded_annotations(book=book, strict_approved=strict_approved)
    typer.echo(json.dumps(build_stats_payload(validated), ensure_ascii=False, indent=2))


@annotations_app.command("export-all")
def export_annotation_bundle(
    book: int = typer.Option(2, min=1, help="Book number to export."),
    strict_approved: bool = typer.Option(
        False,
        "--strict-approved",
        help="Export only the approved subset.",
    ),
    output_dir: OutputDirOption = None,
) -> None:
    """Export processed concepts, relations, graph payload, and stats."""

    validated = _validate_loaded_annotations(book=book, strict_approved=strict_approved)
    paths = export_all(validated, book=book, output_dir=output_dir)
    typer.echo(str(paths.passages_path))
    typer.echo(str(paths.concepts_path))
    typer.echo(str(paths.relations_path))
    typer.echo(str(paths.graph_path))
    typer.echo(str(paths.graphml_path))
    typer.echo(str(paths.stats_path))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
