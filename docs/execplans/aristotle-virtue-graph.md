# Aristotle Virtue Graph MVP for Nicomachean Ethics Book II

This document is a living implementation plan. The sections `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept
current during execution.

## Purpose / Big Picture

Build a small but complete, evidence-first knowledge graph for Aristotle's virtue ethics
using *Nicomachean Ethics* Book II.

After this work, a user should be able to:

1. ingest Book II from an approved source
2. segment it into stable passages
3. build structured concepts and relations with evidence
4. export graph files
5. inspect the graph in a local visualization app

This MVP must stay narrow. It should not attempt the whole work or a generalized philosophy
platform.

## Scope

In scope:

- Book II ingestion
- stable passage records
- concept and relation schemas
- human-reviewed seed annotations
- graph exports
- local visualization
- tests and docs

Out of scope:

- whole corpus extraction
- Greek alignment
- external graph databases
- chatbot behavior
- fully automatic annotation

## Repository Orientation

The implementation is centered in:

- `src/aristotle_graph/ingest/` for source adapters and normalization
- `src/aristotle_graph/annotations/` for annotation models, validation, and processed export
- `src/aristotle_graph/graph/` for graph construction and interoperability export
- `src/aristotle_graph/viewer/` for local viewer loading, filtering, and rendering helpers
- `src/aristotle_graph/app/` for the Streamlit app entrypoint
- `annotations/` for human-reviewed seed data
- `docs/` for data model, source policy, and annotation rules

## Source Policy

Use a redistributable source as the canonical committed source when possible.
MIT pages may be used for verification but should not be treated as the canonical committed
raw corpus if rights are unclear.
Every passage must record `source_id`, `source_url`, and a human-readable citation label.

## Milestone 0: Scaffold the repository

Create the package structure, pyproject, Makefile, tests folder, docs skeleton, and root
`AGENTS.md`.
Add basic commands so a new contributor can install dependencies, run tests, lint, and
launch the app.

Acceptance:

- package imports cleanly
- pytest runs
- ruff runs
- mypy runs on at least the core package

## Milestone 1: Ingest and segment Book II

Implement source adapters and normalization.
Build a stable segmentation pipeline for Book II.
Write `data/interim/book2_passages.jsonl`.

Acceptance:

- repeated runs produce stable `passage_id` values
- every passage has source metadata
- passage ordering is deterministic

## Milestone 2: Define schemas and seed annotations

Implement Pydantic plus JSON Schema validation for concepts, relations, and evidence.
Create split candidate and approved annotation files for the initial principle nodes, virtue
clusters, vice nodes, and action domains.

Acceptance:

- schema validation passes
- every seed relation points to valid evidence passages
- no relation without evidence is accepted

## Milestone 3: Build graph exports

Convert validated seeds plus passage records into processed graph artifacts.

Export:

- `data/processed/book2_passages.jsonl`
- `data/processed/book2_concepts.jsonl`
- `data/processed/book2_relations.jsonl`
- `data/processed/book2_graph.json`
- `data/processed/book2_graph.graphml`
- `data/processed/book2_stats.json`

Acceptance:

- build command completes from a clean checkout after dependencies are installed
- export files load without errors
- graph stats command reports node and edge counts

## Milestone 4: Build the local viewer

Implement a local app with:

- graph view
- passage explorer
- concept explorer
- stats panel

Clicking a concept should show evidence passages and related concepts.

Acceptance:

- app launches locally
- at least one virtue can be explored end to end
- evidence passages are visible in the UI

## Milestone 5: Final polish

Review code, tighten docs, improve naming, and remove accidental complexity.

Acceptance:

- README gives a complete quickstart
- data model and source policy docs are complete
- tests, lint, and type checks pass

## Data Model Rules

The graph must distinguish:

- explicit textual content
- editorial normalization
- interpretation

Use `source_scope` with one of:

- `explicit_text`
- `normalized_editorial`
- `interpretive`

No non-hierarchical relation may exist without evidence.
Keep identifiers stable and human-readable.

## Progress

- [x] Milestone 0 scaffold complete
- [x] Milestone 1 ingestion and segmentation complete
- [x] Milestone 2 schemas and seed annotations complete
- [x] Milestone 3 graph exports complete
- [x] Milestone 4 local viewer complete
- [x] Milestone 5 polish complete

## Surprises & Discoveries

- The repository started empty, so `AGENTS.md` and this execution plan had to be created
  before Milestone 0 could begin.
- Wikisource exposes clean `Part 1` to `Part 9` headings for Book II and supports a pinned
  `oldid` URL, which is promising for stable segmentation.
- MIT Book II is useful as a verification source, but its page source includes an explicit
  site-presentation copyright notice.
- MIT uses at least one section transition with a single `<BR>` before the section number
  (`5 -> 6`), so the verification adapter must normalize both single-break and double-break
  chapter markers.
- The live Wikisource and MIT normalization runs now agree on the same 9-section structure for
  Book II, yielding a 45-passage interim export.
- JSON Schema plus Pydantic validation worked well for Milestone 2 without adding a heavy
  annotation framework.
- Several Book II vice labels are cleaner as repo ids than as Ross surface forms
  (`lack-of-spirit`, `self-deprecation`, `obsequiousness`), so the candidate layer keeps the
  ids stable while preserving Ross wording in `source_labels`.
- The approved pathway stayed safe while the approved files were empty templates, and it now
  supports a genuinely reviewed Book II core without changing the architecture.
- The processed viewer works better when approved-mode exports still include the full Book II
  passage set, even if the approved concept and relation subset is empty.
- `networkx.write_graphml` is sufficient for the interoperability export as long as nested
  fields are flattened into predictable strings first.
- A concept-centered ego graph is much more readable than trying to render the full Book II
  graph in one local view.
- Keeping this project inside the parent `MESOTES` git repository would blur project boundaries,
  so the clean publish path is to give `Aristotle Virtue Graph` its own standalone git history.
- The repo became much easier to scan once the README led with a real viewer preview, a
  `courage` walkthrough, and concrete counts rather than methodology first.

## Decision Log

- 2026-04-09: Use the provided plan from
  `/Users/hanzhenzhu/Downloads/Aristotle_Virtue_Graph_Codex_Plan.md` as the bootstrap source
  for the initial repo documents because the workspace was empty.
- 2026-04-09: Treat Wikisource Ross Book II as the Milestone 1 canonical ingest target and
  MIT Book II as the verification source.
- 2026-04-09: Keep raw downloaded HTML local in `data/raw/` until the repository has a
  clearer raw-text redistribution policy.
- 2026-04-09: Pin the canonical Wikisource adapter to the `oldid=11905514` URL so repeated
  runs do not depend on future upstream edits to the page.
- 2026-04-09: Use section-based stable IDs of the form `ne.b2.s{section}.p{paragraph}` rather
  than HTML anchor numbers, because section labels are semantically meaningful and source-anchor
  numbering is presentation-specific.
- 2026-04-09: Use `annotations/book2/*.candidate.yaml` and `*.approved.yaml` rather than one
  mixed file so candidate and reviewed material stay cleanly separable.
- 2026-04-09: Use `data/interim/book2_passages.jsonl` as the sole passage authority for
  Milestone 2 validation and exports.
- 2026-04-09: Keep strict approved export working with empty approved templates rather than
  auto-approving model-generated seeds, then promote only a small reviewed core once a human
  review step is explicitly confirmed.
- 2026-04-09: Export processed passages from the authoritative Book II passage file in both
  candidate and approved modes so downstream tools always have stable evidence text available.
- 2026-04-09: Treat `book2_graph.json` as the primary rich graph payload and GraphML as a
  flattened interoperability export.
- 2026-04-09: Implement the local viewer as a small Streamlit app over processed exports rather
  than adding a database or custom frontend build system.
- 2026-04-09: Default the viewer to candidate mode and show an explicit empty-state notice when
  approved mode has no reviewed concepts or relations yet.
- 2026-04-09: Split `Aristotle Virtue Graph` into its own git repository before GitHub
  publication so it does not remain entangled with the unrelated parent `MESOTES` repository.
- 2026-04-09: Publish the standalone repository publicly at
  `https://github.com/hanzhenzhujene/aristotle-virtue-graph` after the README and docs were
  polished around the actual Book II findings.
- 2026-04-09: Add a real viewer screenshot, a compact overview graphic, a viewer guide, and a
  code license so the public repository reads like a usable research artifact rather than a
  toolchain dump.
- 2026-04-09: Improve the local viewer's first-run path by defaulting the concept selector to
  `courage` when it is visible.

## Outcomes & Retrospective

Milestones 0 through 4 are complete.
Milestone 5 polish is now complete as well.

Outputs:

- repo scaffold with docs, tooling, tests, CLI commands, and a local viewer
- `data/interim/book2_wikisource_ross_1908_normalized.json`
- `data/interim/book2_mit_archive_ross_normalized.json`
- `data/interim/book2_passages.jsonl`
- `schemas/evidence.schema.json`
- `schemas/concept.schema.json`
- `schemas/relation.schema.json`
- `annotations/book2/concepts.candidate.yaml`
- `annotations/book2/relations.candidate.yaml`
- `annotations/book2/concepts.approved.yaml`
- `annotations/book2/relations.approved.yaml`
- `data/processed/book2_passages.jsonl`
- `data/processed/book2_concepts.jsonl`
- `data/processed/book2_relations.jsonl`
- `data/processed/book2_graph.json`
- `data/processed/book2_graph.graphml`
- `data/processed/book2_stats.json`
- `data/processed/approved/book2_passages.jsonl`
- `data/processed/approved/book2_concepts.jsonl`
- `data/processed/approved/book2_relations.jsonl`
- `data/processed/approved/book2_graph.json`
- `data/processed/approved/book2_graph.graphml`
- `data/processed/approved/book2_stats.json`
- `docs/assets/viewer-courage-candidate.png`
- `docs/assets/book2-overview.svg`
- `docs/viewer_guide.md`
- `LICENSE`
- `src/aristotle_graph/viewer/`
- `src/aristotle_graph/app/streamlit_app.py`

Observed results:

- Book II normalizes to 9 sections
- the canonical interim export contains 45 passages
- repeated segmentation runs produced the same SHA-256 for
  `data/interim/book2_passages.jsonl`
- candidate annotation validation currently exports 54 concepts and 42 relations
- strict approved mode now validates and exports a reviewed subset of 26 concepts and
  21 relations
- processed passage export now carries all 45 authoritative Book II passages in both candidate
  and approved modes
- GraphML export loads successfully as a flattened representation of the processed graph
- the local Streamlit app launches successfully and supports concept, passage, graph, and stats
  views over candidate and approved processed data
- the README now leads with the actual Book II findings and the practical value of the graph,
  rather than only describing the toolchain
- the public-facing repo now includes a real viewer preview, a compact overview graphic, a
  viewer guide, and a code license
- the project now lives in its own public GitHub repository rather than remaining nested inside
  the unrelated parent `MESOTES` repository
- `pytest`, `ruff check .`, and `mypy src/` all pass

Known limitations:

- Bekker references and CTS URNs are not yet populated
- the approved subset is intentionally small and still needs broader human review and promotion
  work before the rest of Book II should be treated as reviewed
- GraphML intentionally flattens nested structures, so `book2_graph.json` remains the richer
  downstream format

Next recommended step:

- continue promoting the remaining Book II clusters after passage-by-passage review so approved
  mode covers more than the current core
