from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from aristotle_graph.viewer.load import ViewerDataset


@dataclass(frozen=True)
class DatasetBundle:
    filename: str
    payload: bytes


@dataclass(frozen=True)
class DownloadArtifact:
    key: str
    label: str
    filename: str
    mime: str
    description: str
    payload: bytes
    size_bytes: int


def _manifest_text(dataset: ViewerDataset) -> str:
    return "\n".join(
        [
            "Aristotle Virtue Graph",
            "Book II dataset bundle",
            "",
            f"Concepts: {dataset.stats.get('concept_count', len(dataset.concepts))}",
            f"Relations: {dataset.stats.get('relation_count', len(dataset.relations))}",
            f"Passages: {dataset.stats.get('passage_count', len(dataset.passages))}",
            "",
            "Each file is copied directly from the processed exports committed in",
            "`data/processed/`.",
            "",
            "Included files:",
            "- book2_passages.jsonl",
            "- book2_concepts.jsonl",
            "- book2_relations.jsonl",
            "- book2_graph.json",
            "- book2_graph.graphml",
            "- book2_stats.json",
        ]
    )


def build_dataset_bundle(dataset: ViewerDataset) -> DatasetBundle:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for path in (
            dataset.paths.passages_path,
            dataset.paths.concepts_path,
            dataset.paths.relations_path,
            dataset.paths.graph_path,
            dataset.paths.graphml_path,
            dataset.paths.stats_path,
        ):
            archive.write(path, arcname=path.name)
        archive.writestr("README.txt", _manifest_text(dataset))

    return DatasetBundle(
        filename="aristotle-virtue-graph-book2-dataset.zip",
        payload=buffer.getvalue(),
    )


def _artifact_from_path(
    *,
    key: str,
    label: str,
    path: Path,
    mime: str,
    description: str,
) -> DownloadArtifact:
    return DownloadArtifact(
        key=key,
        label=label,
        filename=path.name,
        mime=mime,
        description=description,
        payload=path.read_bytes(),
        size_bytes=path.stat().st_size,
    )


def build_download_artifacts(dataset: ViewerDataset) -> tuple[DownloadArtifact, ...]:
    bundle = build_dataset_bundle(dataset)
    return (
        DownloadArtifact(
            key="bundle",
            label="Full dataset bundle (.zip)",
            filename=bundle.filename,
            mime="application/zip",
            description="All processed Book II exports plus a tiny manifest.",
            payload=bundle.payload,
            size_bytes=len(bundle.payload),
        ),
        _artifact_from_path(
            key="passages",
            label="Passages (.jsonl)",
            path=dataset.paths.passages_path,
            mime="application/octet-stream",
            description="The authoritative processed passage records used by the viewer.",
        ),
        _artifact_from_path(
            key="concepts",
            label="Concepts (.jsonl)",
            path=dataset.paths.concepts_path,
            mime="application/octet-stream",
            description="Reviewed concept records with evidence links and metadata.",
        ),
        _artifact_from_path(
            key="relations",
            label="Relations (.jsonl)",
            path=dataset.paths.relations_path,
            mime="application/octet-stream",
            description="Reviewed relation records linking concepts through cited passages.",
        ),
        _artifact_from_path(
            key="graph-json",
            label="Graph payload (.json)",
            path=dataset.paths.graph_path,
            mime="application/json",
            description="Rich node-link graph export for downstream apps and analysis.",
        ),
        _artifact_from_path(
            key="graph-graphml",
            label="GraphML (.graphml)",
            path=dataset.paths.graphml_path,
            mime="application/octet-stream",
            description="Flattened interoperability export for graph tools.",
        ),
        _artifact_from_path(
            key="stats",
            label="Stats (.json)",
            path=dataset.paths.stats_path,
            mime="application/json",
            description="Counts by concept kind, relation type, and assertion tier.",
        ),
    )
