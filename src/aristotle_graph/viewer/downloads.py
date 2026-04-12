from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from aristotle_graph.viewer.load import ViewerDataset


@dataclass(frozen=True)
class DownloadArtifact:
    key: str
    label: str
    filename: str
    mime: str
    payload: bytes
    description: str


@dataclass(frozen=True)
class DatasetBundle:
    filename: str
    payload: bytes


def _book_number(dataset: ViewerDataset) -> int:
    if "book" in dataset.stats:
        return int(dataset.stats["book"])
    if dataset.passages:
        return dataset.passages[0].book_number
    return 2


def _book_slug(dataset: ViewerDataset) -> str:
    return f"book{_book_number(dataset)}"


def _required_paths(dataset: ViewerDataset) -> tuple[Path, ...]:
    return (
        dataset.paths.passages_path,
        dataset.paths.concepts_path,
        dataset.paths.relations_path,
        dataset.paths.graph_path,
        dataset.paths.graphml_path,
        dataset.paths.stats_path,
    )


def _read_artifact_bytes(path: Path) -> bytes:
    if not path.exists():
        msg = f"Missing dataset artifact: {path}"
        raise FileNotFoundError(msg)
    return path.read_bytes()


def _manifest_text(dataset: ViewerDataset) -> str:
    book_slug = _book_slug(dataset)
    included_files = [path.name for path in _required_paths(dataset)]
    return "\n".join(
        [
            "Aristotle Virtue Graph",
            f"{book_slug.capitalize()} dataset bundle",
            "",
            f"Concepts: {dataset.stats.get('concept_count', len(dataset.concepts))}",
            f"Relations: {dataset.stats.get('relation_count', len(dataset.relations))}",
            f"Passages: {dataset.stats.get('passage_count', len(dataset.passages))}",
            "",
            "Included files:",
            *[f"- {name}" for name in included_files],
        ]
    )


def _file_artifacts(dataset: ViewerDataset) -> tuple[DownloadArtifact, ...]:
    return (
        DownloadArtifact(
            key="passages",
            label="Passages (.jsonl)",
            filename=dataset.paths.passages_path.name,
            mime="application/x-ndjson",
            payload=_read_artifact_bytes(dataset.paths.passages_path),
            description="Authoritative processed passage rows for the current book.",
        ),
        DownloadArtifact(
            key="concepts",
            label="Concepts (.jsonl)",
            filename=dataset.paths.concepts_path.name,
            mime="application/x-ndjson",
            payload=_read_artifact_bytes(dataset.paths.concepts_path),
            description="Processed concept annotations with evidence and stable ids.",
        ),
        DownloadArtifact(
            key="relations",
            label="Relations (.jsonl)",
            filename=dataset.paths.relations_path.name,
            mime="application/x-ndjson",
            payload=_read_artifact_bytes(dataset.paths.relations_path),
            description="Processed relation annotations with passage-grounded evidence.",
        ),
        DownloadArtifact(
            key="graph-json",
            label="Graph payload (.json)",
            filename=dataset.paths.graph_path.name,
            mime="application/json",
            payload=_read_artifact_bytes(dataset.paths.graph_path),
            description="Rich node-link graph payload for downstream apps and analysis.",
        ),
        DownloadArtifact(
            key="graphml",
            label="GraphML (.graphml)",
            filename=dataset.paths.graphml_path.name,
            mime="application/graphml+xml",
            payload=_read_artifact_bytes(dataset.paths.graphml_path),
            description="Flattened interoperability graph export for graph tools.",
        ),
        DownloadArtifact(
            key="stats",
            label="Stats (.json)",
            filename=dataset.paths.stats_path.name,
            mime="application/json",
            payload=_read_artifact_bytes(dataset.paths.stats_path),
            description="Top-level counts by concept kind, relation type, and assertion tier.",
        ),
    )


def build_dataset_bundle(dataset: ViewerDataset) -> DatasetBundle:
    file_artifacts = _file_artifacts(dataset)
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for artifact in file_artifacts:
            info = ZipInfo(artifact.filename)
            info.date_time = (2026, 1, 1, 0, 0, 0)
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, artifact.payload)
        readme_info = ZipInfo("README.txt")
        readme_info.date_time = (2026, 1, 1, 0, 0, 0)
        readme_info.compress_type = ZIP_DEFLATED
        archive.writestr(readme_info, _manifest_text(dataset))

    return DatasetBundle(
        filename=f"aristotle-virtue-graph-{_book_slug(dataset)}-dataset.zip",
        payload=buffer.getvalue(),
    )


def build_download_artifacts(dataset: ViewerDataset) -> tuple[DownloadArtifact, ...]:
    bundle = build_dataset_bundle(dataset)
    bundle_artifact = DownloadArtifact(
        key="bundle",
        label="Full dataset bundle (.zip)",
        filename=bundle.filename,
        mime="application/zip",
        payload=bundle.payload,
        description=(
            "Everything in one zip: passages, concepts, relations, graph payload, "
            "GraphML, stats, and a manifest."
        ),
    )
    return (bundle_artifact, *_file_artifacts(dataset))
