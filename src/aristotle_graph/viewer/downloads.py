from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from aristotle_graph.viewer.load import ViewerDataset


@dataclass(frozen=True)
class DatasetBundle:
    filename: str
    payload: bytes


def _manifest_text(dataset: ViewerDataset) -> str:
    return "\n".join(
        [
            "Aristotle Virtue Graph",
            "Reviewed Book II dataset bundle",
            "",
            f"Concepts: {dataset.stats.get('concept_count', len(dataset.concepts))}",
            f"Relations: {dataset.stats.get('relation_count', len(dataset.relations))}",
            f"Passages: {dataset.stats.get('passage_count', len(dataset.passages))}",
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
        filename="aristotle-virtue-graph-book2-reviewed-dataset.zip",
        payload=buffer.getvalue(),
    )
