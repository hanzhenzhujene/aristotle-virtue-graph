# Aristotle Virtue Graph

An evidence-first knowledge graph for Aristotle's *Nicomachean Ethics* Book II.

This project turns Book II into a passage-grounded graph of concepts, relations, and evidence.
Its goal is not to build a chatbot or a giant philosophy ontology. Its goal is to make the
argument structure of Book II inspectable, reviewable, and reusable without losing contact
with the text.

## The takeaway

Book II presents a practical architecture of moral formation:

- moral virtue is not produced by nature; it is formed by habit
- virtue is tracked by pleasure and pain
- virtue is a state of character, not a passion or a faculty
- acting virtuously requires knowledge, choice, and a firm state
- virtue aims at a mean relative to us, guided by right reason and the practically wise
- specific virtues can be modeled as stable triads:
  virtue -> excess -> deficiency, within a determinate domain

The graph makes those claims explicit and traceable.
Every concept and every non-hierarchical relation must point back to one or more Book II
passages.

## Why this repo is useful

Most summaries of Aristotle flatten Book II into slogans.
This repo does something more instrumental:

- it separates textual claims from editorial normalization and interpretation
- it preserves a stable passage authority
- it distinguishes candidate annotations from approved ones
- it exports machine-usable graph artifacts without hiding the evidence
- it lets a reader move directly from concept -> relation -> passage

If you want to know not just what the repo claims, but where Book II supports it, this is the
point of the project.

## Current findings

Current Book II dataset status:

- 45 deterministic passages across 9 sections
- 54 total concepts in candidate mode
- 42 total relations in candidate mode
- 26 approved concepts in the reviewed core
- 21 approved relations in the reviewed core

What is already reviewed in strict approved mode:

- the opening distinction between moral and intellectual virtue
- moral virtue as formed by habituation
- the role of pleasure and pain in moral formation
- virtue as a state of character rather than passion or faculty
- the conditions of virtuous action: knowledge, choice, and stability
- the mean as determined by right reason and the practically wise person
- two fully reviewed virtue triads:
  courage / rashness / cowardice in the domain of fear and confidence
  temperance / self-indulgence / insensibility in the domain of bodily pleasures and pains

This means the repository already supports a strong, evidence-backed reading of Book II's core
practical thesis:
Aristotle is not merely classifying virtues; he is describing how character is formed,
recognized, and judged.

## What the app lets you do

The local viewer is read-only and evidence-first.

You can:

- browse the graph in `candidate` or `approved` mode
- inspect a concept and see its incoming and outgoing relations
- open the exact passages used as evidence
- explore a 1-hop or 2-hop ego graph around a selected concept
- compare the larger candidate layer with the smaller reviewed core

The main happy path is:

1. choose a concept such as `courage`
2. inspect its relations
3. open the linked passage
4. confirm the claim against the text

## Project principles

- Scope is limited to *Nicomachean Ethics* Book II.
- Every concept must have evidence.
- Every relation must have evidence.
- Non-hierarchical relations are never allowed without a supporting passage.
- Ross wording is preserved in `source_labels`.
- Modernized wording belongs in `aliases`, not in the source field.
- Textual, editorial, and interpretive layers are kept distinct.
- LLM-generated annotations are never treated as automatic ground truth.

## Source policy

- Preferred canonical ingest source for Book II: the Ross translation on Wikisource
- Verification source: MIT Internet Classics Book II page
- MIT may be used for verification, but it is not treated as the committed canonical raw corpus
- Raw downloaded HTML stays local; the committed passage authority is the derived file
  `data/interim/book2_passages.jsonl`

See [docs/source_policy.md](docs/source_policy.md) for the fuller rationale.

## Quickstart

Prerequisites:

- Python 3.11 or newer
- a local virtual environment

Install and run:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev,viewer]"
make annotations-export
make annotations-export-strict
make app
```

If you only need the export pipeline and not the viewer, `pip install -e ".[dev]"` is enough.

## Canonical workflow

Build processed artifacts:

```bash
make annotations-validate
make annotations-validate-strict
make annotations-export
make annotations-export-strict
make annotations-stats
```

Run the viewer:

```bash
make app
```

Equivalent direct command:

```bash
python -m streamlit run src/aristotle_graph/app/streamlit_app.py
```

Run checks:

```bash
make test
make lint
make typecheck
make check
```

## Data artifacts

Authoritative passage source:

- `data/interim/book2_passages.jsonl`

Candidate-mode processed artifacts:

- `data/processed/book2_passages.jsonl`
- `data/processed/book2_concepts.jsonl`
- `data/processed/book2_relations.jsonl`
- `data/processed/book2_graph.json`
- `data/processed/book2_graph.graphml`
- `data/processed/book2_stats.json`

Strict approved-mode processed artifacts:

- `data/processed/approved/book2_passages.jsonl`
- `data/processed/approved/book2_concepts.jsonl`
- `data/processed/approved/book2_relations.jsonl`
- `data/processed/approved/book2_graph.json`
- `data/processed/approved/book2_graph.graphml`
- `data/processed/approved/book2_stats.json`

`book2_graph.json` is the primary rich graph payload.
`book2_graph.graphml` is a flattened interoperability export.

## Review workflow

Human-editable annotation files live in:

- `annotations/book2/concepts.candidate.yaml`
- `annotations/book2/relations.candidate.yaml`
- `annotations/book2/concepts.approved.yaml`
- `annotations/book2/relations.approved.yaml`

The working rule is simple:

- new or machine-assisted annotations begin as `candidate`
- only human-reviewed items move to `approved`
- strict export mode uses only the approved layer

This repository already includes a reviewed core, so approved mode is usable immediately.

## Repository layout

- `src/aristotle_graph/ingest/`: source adapters, normalization, segmentation
- `src/aristotle_graph/annotations/`: schemas, loaders, validation, export
- `src/aristotle_graph/graph/`: graph payload construction and GraphML export
- `src/aristotle_graph/viewer/`: viewer loading, filtering, and rendering helpers
- `src/aristotle_graph/app/`: Streamlit entrypoint
- `annotations/`: candidate and approved Book II annotation files
- `data/`: interim and processed outputs
- `docs/`: data model, annotation guide, source policy, and execution plan

## Limits

- This is Book II only.
- There is no database.
- There is no chatbot or RAG layer.
- The approved subset is still intentionally smaller than the candidate layer.
- Bekker references and CTS URNs are not yet populated.

## Next step

The next meaningful extension is not more software complexity.
It is more review:

- continue promoting the remaining Book II virtue clusters from candidate to approved
- keep every promotion passage-grounded
- grow the approved graph without weakening the evidence standard

See [docs/annotation_guide.md](docs/annotation_guide.md),
[docs/data_model.md](docs/data_model.md), and
[docs/execplans/aristotle-virtue-graph.md](docs/execplans/aristotle-virtue-graph.md).
