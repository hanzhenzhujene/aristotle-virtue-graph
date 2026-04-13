# Aristotle Virtue Graph <img src="docs/assets/aristotle-head-icon.png" alt="Aristotle head icon" width="48" />

> A reviewed, passage-grounded dashboard and dataset for exploring *Nicomachean Ethics* Book II.

<sub>by Jenny Zhu · <a href="https://www.linkedin.com/in/hanzhen-zhu/"><img src="docs/assets/linkedin-icon.svg" alt="LinkedIn" width="12" /></a></sub>

This repository turns Aristotle's Book II into something you can inspect rather than merely summarize.
The public app lets you move between concepts, relations, and exact supporting passages, while the
processed exports keep the same structure available for reuse in JSONL, JSON, and GraphML.

| Live dashboard | Run locally | Viewer guide |
| --- | --- | --- |
| **[Open live dashboard](https://aristotle-virtue-graph.streamlit.app/)** | [`make app`](#run-the-viewer) | [docs/viewer_guide.md](docs/viewer_guide.md) |

![Home dashboard preview](docs/assets/viewer-home-hero.png)

_The reviewed Book II home screen, with direct paths into a virtue, a formation concept, and a passage-first reading route._

## Submission Snapshot

- Scope: *Nicomachean Ethics* Book II only
- Public dataset: `45` passages, `54` reviewed concepts, `42` reviewed relations
- Public app: reviewed-only Streamlit dashboard at [aristotle-virtue-graph.streamlit.app](https://aristotle-virtue-graph.streamlit.app/)
- Public exports: `data/processed/book2_passages.jsonl`, `book2_concepts.jsonl`, `book2_relations.jsonl`, `book2_graph.json`, `book2_graph.graphml`, `book2_stats.json`
- Constraints held: no database, no chatbot, no hidden LLM ground truth, Book II boundary respected

## Start Here

If you only try one path, use `courage`.

1. Open the live dashboard.
2. Click `Open courage`.
3. Read the concept header and triad strip.
4. Open the supporting passage `NE II.7 ¶1`.
5. Return to the local map or overall map and click a neighboring concept.

What that path shows:

```text
courage
= the mean with respect to fear and confidence

has_deficiency -> cowardice
has_excess     -> rashness
concerns       -> fear and confidence

evidence -> NE II.7 ¶1
```

That is the core claim of the project:
the graph is not floating above the text.
It stays attached to the passage that supports it.

![Concept explorer preview](docs/assets/viewer-courage-hero.png)

_Concept Explorer focused on `courage`, showing the virtue triad, local map, and supporting passage route._

## What This Submission Delivers

- A live, read-only dashboard for exploring Book II through `Home`, `Concept Explorer`, `Passage Explorer`, `Overall Map`, and `Stats`
- A reviewed Book II graph with stable concept ids, stable relation ids, and evidence records attached to every concept and relation
- A processed dataset in simple local files that can be inspected without running the app
- A deterministic validation and export pipeline for rebuilding the reviewed public artifacts from annotation files
- A small but reusable graph corpus suitable for close reading, graph analysis, teaching, and structured NLP experiments

## What You Can Do Here

- Browse Book II as a graph rather than a flat outline.
- Start from a concept and move outward through its direct relations and nearby map neighbors.
- Start from a passage and see which concepts and relations are grounded there.
- Click nodes in the local map or overall map to navigate directly into the relevant concept page.
- Download the full Book II bundle or a single processed artifact from the app sidebar.

## Coverage in This Submission

The reviewed Book II dataset covers:

- the distinction between moral and intellectual virtue
- habituation
- pleasure and pain as markers of formation
- virtue as a state of character rather than passion or faculty
- the conditions of virtuous action: knowledge, choice, and stability
- the mean as guided by right reason and the practically wise person
- courage / rashness / cowardice
- temperance / self-indulgence / insensibility
- liberality / prodigality / meanness
- magnificence / vulgarity / niggardliness
- proper pride / empty vanity / undue humility
- good temper / irascibility / inirascibility
- truthfulness / boastfulness / mock modesty
- wit / buffoonery / boorishness
- friendliness / obsequiousness / quarrelsomeness

## Why The Data Is Trustworthy

- Every concept cites one or more passages.
- Every relation cites one or more passages.
- The public app runs on the reviewed dataset in `data/processed/`, not on draft annotations.
- `source_labels` preserve Ross wording instead of silently replacing it with modern paraphrase.
- The project keeps explicit textual claims, editorial normalization, and interpretation separate in the data model.
- Book II is a hard boundary for this submission; later books are roadmap only.

## Run The Viewer

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[viewer]"
make app
```

This opens the local dashboard on `Home` against the committed reviewed Book II exports.
Recommended first click: `Open courage`.

## Rebuild The Reviewed Exports

Use this only if you want to regenerate the reviewed processed artifacts from the annotation files.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev,viewer]"
make annotations-validate
make annotations-validate-strict
make annotations-export
make app
```

`make annotations-export` writes the reviewed public dataset to `data/processed/`.

## Viewer At A Glance

| View | What it is for |
| --- | --- |
| Home | Understand the project quickly and enter through the strongest Book II routes |
| Concept Explorer | Read one concept closely, inspect its local map, and move through linked concepts and passages |
| Passage Explorer | Read the text itself and see which graph claims are grounded there |
| Overall Map | Explore the whole filtered Book II network and navigate by node click |
| Stats | Inspect dataset counts by concept kind, relation type, and assertion tier |

More detail: [docs/viewer_guide.md](docs/viewer_guide.md)

## Files You Can Reuse

Authoritative segmented passage source:

- `data/interim/book2_passages.jsonl`

Public reviewed exports:

- `data/processed/book2_passages.jsonl`
- `data/processed/book2_concepts.jsonl`
- `data/processed/book2_relations.jsonl`
- `data/processed/book2_graph.json`
- `data/processed/book2_graph.graphml`
- `data/processed/book2_stats.json`

`book2_graph.json` is the primary rich export.
`book2_graph.graphml` is a flattened interoperability export.

## Source Policy

- Preferred canonical ingest source for Book II: the Ross translation on Wikisource
- Verification source: MIT Internet Classics Book II page
- MIT is used for verification when helpful, but it is not treated as the committed canonical raw corpus
- Raw downloaded HTML stays local; the committed passage authority is the derived file `data/interim/book2_passages.jsonl`

Full rationale: [docs/source_policy.md](docs/source_policy.md)

## Repository Guide

- `src/aristotle_graph/ingest/`: source adapters, normalization, segmentation
- `src/aristotle_graph/annotations/`: schemas, loaders, validation, export
- `src/aristotle_graph/graph/`: graph payload construction and GraphML export
- `src/aristotle_graph/viewer/`: viewer loading, filtering, rendering, and dataset bundle helpers
- `src/aristotle_graph/app/`: Streamlit app logic
- `streamlit_app.py`: deployment-friendly root entrypoint
- `annotations/`: maintainer-facing Book II annotation files
- `data/`: interim and processed outputs
- `docs/`: user and maintainer docs

Useful docs:

- [docs/viewer_guide.md](docs/viewer_guide.md)
- [docs/deployment.md](docs/deployment.md)
- [docs/annotation_guide.md](docs/annotation_guide.md)
- [docs/data_model.md](docs/data_model.md)
- [docs/roadmap.md](docs/roadmap.md)
- [docs/source_policy.md](docs/source_policy.md)
- [docs/execplans/aristotle-virtue-graph.md](docs/execplans/aristotle-virtue-graph.md)

## Roadmap

The next meaningful expansion is more Aristotle, not more interface complexity.
The clearest next path is:

- Book III, to complete courage, temperance, voluntary action, and choice
- Book IV, to add the dense run of practical virtue triads
- Book VI, to explain practical wisdom as the hinge that guides the mean
- Book X, to connect the network back to happiness, pleasure, and the good life

Full note: [docs/roadmap.md](docs/roadmap.md)

## Limits

- This submission is Book II only.
- There is no database.
- There is no chatbot or RAG layer.
- The graph is reviewed and passage-grounded, but it is not a full ontology of Aristotle.
- Bekker references and CTS URNs are not yet populated.

## License

Code in this repository is released under the [MIT License](LICENSE).
Text provenance and redistribution constraints are described in [docs/source_policy.md](docs/source_policy.md).
