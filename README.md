# Aristotle Virtue Graph <img src="docs/assets/aristotle-head-icon.png" alt="Aristotle head icon" width="50" />

> A reviewed, passage-grounded dashboard for exploring *Nicomachean Ethics* Book II. **[Open live dashboard](https://aristotle-virtue-graph.streamlit.app/)**
>
> <sub>by Jenny Zhu <a href="https://www.linkedin.com/in/hanzhen-zhu/"><img src="docs/assets/linkedin-icon.svg" alt="LinkedIn" width="14" style="vertical-align:text-bottom; margin-left:4px;" /></a></sub>

This project turns Book II into something you can inspect instead of merely summarize.
Open a concept like `courage`, click through its neighboring nodes, read the supporting passage,
and download the structured dataset that drives the app.

🏛️ **Book II only** · 📜 **45 passages** · 🧠 **54 reviewed concepts** · 🔗 **42 reviewed relations**

![Dashboard hero](docs/assets/viewer-courage-candidate.png)

_Hero view: the dashboard centered on `courage`, with concept reading, passage grounding, and graph navigation in one place._

## Open the dashboard

| Live dashboard | Run locally | Viewer guide |
| --- | --- | --- |
| **[Open live dashboard](https://aristotle-virtue-graph.streamlit.app/)** | **Run now:** [`make app`](#run-the-viewer) | [Viewer guide](docs/viewer_guide.md) |

_The live app is running on Streamlit Community Cloud. Deployment notes stay in [docs/deployment.md](docs/deployment.md)._

## Run the viewer

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[viewer]"
make app
```

This opens the dashboard immediately against the committed reviewed Book II exports.
Start with `courage`.

## Try this first

1. Open the dashboard.
2. Click `Open courage`.
3. Read the short summary at the top of Concept Explorer.
4. Open the supporting passage `NE II.7 ¶1`.
5. Use the small concept map on the same page, or open `Overall Map`, and click a neighboring node.

What you should see:

```text
courage
|- has_excess      -> rashness
|- has_deficiency -> cowardice
`- concerns       -> fear and confidence

evidence: NE II.7 ¶1
```

That path shows the point of the repo:
the graph is not a summary layer floating above the text.
It stays attached to the passage that supports it.

## What you can do here

- Browse Book II as a reviewed graph instead of a flat outline.
- Read a concept in plain language before opening the structured metadata.
- Start from a passage and see which concepts and relations are grounded there.
- Click nodes in the embedded concept map or the overall map to navigate into Concept Explorer.
- Download the reviewed Book II dataset for NLP, graph analysis, or close reading work.

## Rebuild exported data

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

`make annotations-export` now writes the reviewed public dataset to `data/processed/`.

## Why it is interesting

Book II is often reduced to a few slogans about habit and the mean.
This repo makes the internal structure navigable in a more useful form:

- virtues and vices appear as linked claims rather than isolated definitions
- every concept and every non-hierarchical relation stays passage-grounded
- the graph can be audited back to specific sections and paragraph-level passages
- the reviewed dataset is small enough to inspect and concrete enough to reuse

## Current state

The reviewed Book II dataset currently covers:

- the distinction between moral and intellectual virtue
- habituation
- pleasure and pain as markers of formation
- virtue as a state of character rather than passion or faculty
- the conditions of virtuous action: knowledge, choice, and stability
- the mean as guided by right reason and the practically wise person
- all nine virtue clusters represented in this MVP:
  courage / rashness / cowardice
  temperance / self-indulgence / insensibility
  liberality / prodigality / meanness
  magnificence / vulgarity / niggardliness
  proper pride / empty vanity / undue humility
  good temper / irascibility / inirascibility
  truthfulness / boastfulness / mock modesty
  wit / buffoonery / boorishness
  friendliness / obsequiousness / quarrelsomeness

The repository now also includes a reviewed Book III starter slice for downstream graph work:

- 65 authoritative Book III passages
- 19 reviewed concepts
- 16 reviewed relations
- focused on voluntary and involuntary action, choice and deliberation, courage, and temperance

The live app still runs on Book II only.

## Viewer at a glance

| View | What it is for |
| --- | --- |
| Home | Understand the job of the app and jump into the strongest first paths |
| Concept Explorer | Read one concept closely, inspect its small local graph, then move through linked concepts and passages |
| Passage Explorer | Start from the text and see which concepts and relations are grounded there |
| Overall Map | Explore the whole filtered Book II network with search, filtering, and hub summaries |
| Stats | See counts by concept kind, relation type, and assertion tier |

More detail: [docs/viewer_guide.md](docs/viewer_guide.md)

## Why the structure is trustworthy

The project stays strict in a few concrete ways:

- Every concept must cite one or more passages.
- Every relation must cite one or more passages.
- `source_labels` preserve Ross wording instead of silently modernizing it.
- Draft material stays in candidate files and does not power the public app by default.
- Book II is a hard boundary; the repo does not quietly expand into later books.

## Data artifacts

Authoritative passage source:

- `data/interim/book2_passages.jsonl`

Book III interim authority and reviewed starter artifacts:

- `data/interim/book3_wikisource_ross_1908_normalized.json`
- `data/interim/book3_mit_archive_ross_normalized.json`
- `data/interim/book3_passages.jsonl`
- `data/processed/book3_passages.jsonl`
- `data/processed/book3_concepts.jsonl`
- `data/processed/book3_relations.jsonl`
- `data/processed/book3_graph.json`
- `data/processed/book3_graph.graphml`
- `data/processed/book3_stats.json`

Public reviewed artifacts:

- `data/processed/book2_passages.jsonl`
- `data/processed/book2_concepts.jsonl`
- `data/processed/book2_relations.jsonl`
- `data/processed/book2_graph.json`
- `data/processed/book2_graph.graphml`
- `data/processed/book2_stats.json`

Compatibility copy of the strict export:

- `data/processed/approved/book2_passages.jsonl`
- `data/processed/approved/book2_concepts.jsonl`
- `data/processed/approved/book2_relations.jsonl`
- `data/processed/approved/book2_graph.json`
- `data/processed/approved/book2_graph.graphml`
- `data/processed/approved/book2_stats.json`

`book2_graph.json` is the primary rich export.
`book2_graph.graphml` is a flattened interoperability export.

## Review workflow

Human-editable annotation files live in:

- `annotations/book2/concepts.candidate.yaml`
- `annotations/book2/relations.candidate.yaml`
- `annotations/book2/concepts.approved.yaml`
- `annotations/book2/relations.approved.yaml`
- `annotations/book3/concepts.candidate.yaml`
- `annotations/book3/relations.candidate.yaml`
- `annotations/book3/concepts.approved.yaml`
- `annotations/book3/relations.approved.yaml`

The public app uses the reviewed Book II set only.
Book III annotations and exports are committed for maintainer and downstream dataset work, not yet
for the live dashboard.
Candidate files remain for future maintainer work, not as a second public mode.

More detail: [docs/annotation_guide.md](docs/annotation_guide.md)

## Source policy

- Preferred canonical ingest source for Book II: the Ross translation on Wikisource
- Verification source: MIT Internet Classics Book II page
- MIT may be used for verification, but it is not treated as the committed canonical raw corpus
- Raw downloaded HTML stays local; the committed passage authority is the derived file
  `data/interim/book2_passages.jsonl`

Full rationale: [docs/source_policy.md](docs/source_policy.md)

## Roadmap

The next meaningful expansion is more Aristotle, not more interface complexity.
Book II is a strong starting slice, but it is still only the opening architecture of the
ethical system. The clearest next path is:

- Book III, to complete courage, temperance, voluntary action, and choice
- Book IV, to add the dense run of practical virtue triads that would make the graph much
  richer to read and compare
- Book VI, to explain practical wisdom as the hinge that guides the mean
- Book X, to connect the network back to happiness, pleasure, and the shape of the good life

That sequence would also broaden the audience.
With Book II alone, the repo is most useful for focused coursework and close reading.
With Books II, III, IV, VI, and X together, it starts to become a serious companion for
students, reading groups, self-directed readers, and researchers building structured datasets.

The repository now has:

- Book III ingestion and deterministic segmentation
- a reviewed Book III starter graph slice for export and inspection

But the public reviewed dashboard remains Book II-only.

Full note: [docs/roadmap.md](docs/roadmap.md)

## Deployment

The live dashboard is running on Streamlit Community Cloud:

- live URL: `https://aristotle-virtue-graph.streamlit.app/`
- app entrypoint: `streamlit_app.py`
- deployment dependencies: `requirements.txt`
- app theme/config: `.streamlit/config.toml`

Deployment notes and the current hosted target are in [docs/deployment.md](docs/deployment.md).

## Repository guide

- `src/aristotle_graph/ingest/`: source adapters, normalization, segmentation
- `src/aristotle_graph/annotations/`: schemas, loaders, validation, export
- `src/aristotle_graph/graph/`: graph payload construction and GraphML export
- `src/aristotle_graph/viewer/`: viewer loading, filtering, rendering, and dataset bundle helpers
- `src/aristotle_graph/app/`: Streamlit app logic
- `streamlit_app.py`: deployment-friendly root entrypoint
- `annotations/`: candidate and approved Book II and Book III annotation files
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

## Limits

- This is Book II only.
- There is no database.
- There is no chatbot or RAG layer.
- The graph is reviewed and passage-grounded, but it is not a full ontology of Aristotle.
- Bekker references and CTS URNs are not yet populated.

## License

Code in this repository is released under the [MIT License](LICENSE).
Text provenance and redistribution constraints are described in [docs/source_policy.md](docs/source_policy.md).
