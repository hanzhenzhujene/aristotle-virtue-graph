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

- concept explorer with an embedded local graph map
- overall map
- passage explorer
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
- [x] 2026-04-11 approved-first viewer refresh complete

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
- The full Book II graph is still readable at this scale if it gets its own page, stronger
  physics/layout tuning, and supporting summaries instead of competing with the ego graph view.
- Keeping this project inside the parent `MESOTES` git repository would blur project boundaries,
  so the clean publish path is to give `Aristotle Virtue Graph` its own standalone git history.
- The repo became much easier to scan once the README led with a real viewer preview, a
  `courage` walkthrough, and concrete counts rather than methodology first.
- Streamlit Community Cloud deployment becomes much clearer when the repository exposes a root
  `streamlit_app.py`, root `requirements.txt`, and a short deployment note instead of assuming
  readers will infer the entrypoint from package internals.
- The README front page works better with one strong dashboard screenshot than with a second
  overview graphic competing for attention before the user has even opened the app.
- Public-facing polish exposed a real compatibility issue: `st.dataframe(width="stretch")`
  breaks on older installed Streamlit versions, so the viewer should prefer the broader
  `use_container_width=True` path for stable local runs.
- Once the live app exists, the README should link directly to the real dashboard URL rather
  than forcing visitors through deployment notes first.
- Streamlit `tabs` are awkward for evidence-driven navigation because buttons elsewhere in the
  page cannot reliably move the user into the relevant tab, so a controlled view selector is a
  better fit when concept or relation evidence should open directly into Passage Explorer.
- Streamlit also forbids mutating the session-state key of an already-instantiated widget in the
  same run, so button-driven view changes need a pending-navigation key that is applied on the
  next rerun rather than writing directly into the `st.radio` state.
- On Streamlit Community Cloud, button-triggered navigation is safer when it uses `on_click`
  callbacks plus queued state changes rather than mutating session state inside the button branch
  itself.
- Extending the reviewed core works best when each added triad is promoted in small, textually
  direct batches rather than trying to approve the rest of section 7 all at once.
- Streamlit app URLs can be shortened from Community Cloud app settings, but that change lives in
  the hosted dashboard configuration rather than in repository code or deployment files.
- A small public-facing icon helps the repo and live app feel more finished, as long as it stays
  secondary to the evidence-first content and does not crowd the first-run path.
- Once the remaining section 7 triads were rechecked, the gap between the draft layer and the
  reviewed layer turned out to be small enough to close completely without changing the schema or
  export architecture.
- Streamlit's inline v2 components are a cleaner fit for graph click-through than trying to force
  bidirectional behavior through `components.html()`, because the component can own an iframe and
  return a clicked node id directly to Python.
- The public app feels much clearer when it has one reviewed data surface, a homepage, and
  dataset download, instead of exposing the repo's candidate-versus-approved workflow directly.
- Book II is enough to prove the evidence-first method, but the clearest long-term product value
  lies in expanding to the later books that complete courage and temperance, add the richer
  practical virtue triads, explain practical wisdom, and connect the system back to happiness.
- The per-concept reading flow becomes more natural when the ego graph is embedded as a small
  local map inside Concept Explorer, rather than split into a separate top-level page.

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
- 2026-04-09: Add root-level deployment files for Streamlit Community Cloud
  (`streamlit_app.py`, `requirements.txt`, `.streamlit/config.toml`) so the public repo has an
  obvious app entrypoint and a clean deployment path.
- 2026-04-09: Make the top README CTA explicitly honest about live status (`coming soon`) until
  a real public Streamlit URL exists, and split first-run instructions from rebuild workflows.
- 2026-04-09: Replace the temporary `coming soon` CTA with the real Streamlit Community Cloud
  URL once deployment is live.
- 2026-04-10: Replace the viewer tabs with a controlled top-level view selector so evidence
  buttons can send the user directly to Passage Explorer without adding a frontend framework.
- 2026-04-10: Promote the liberality and truthfulness triads from candidate to approved after
  rechecking their Book II.7 passage evidence.
- 2026-04-10: Promote the wit and friendliness triads from candidate to approved after
  rechecking the direct wording of `NE II.7 ¶4`.
- 2026-04-10: Document the Streamlit app-settings path for choosing a shorter custom subdomain,
  since shortening the live URL cannot be completed from inside the repo alone.
- 2026-04-10: Add a dedicated `Overall Map` page rather than overloading the ego-graph page, so
  the dashboard can support both close neighborhood reading and whole-graph inspection.
- 2026-04-10: Fix the `Open supporting passage` and related jump buttons by switching the viewer
  to a pending-navigation pattern, because Streamlit rejects direct same-run writes into the
  session-state key of the active view radio.
- 2026-04-10: Follow up on the passage-jump fix by moving the navigation buttons to `on_click`
  callbacks as well, so Community Cloud does not execute the state write from inside the button
  branch.
- 2026-04-10: Replace the earlier repo mark with the supplied Aristotle head PNG and reuse that
  same small raster icon in the README and Streamlit header.
- 2026-04-11: Promote the remaining magnificence, proper-pride, and good-temper triads after
  rechecking `NE II.7 ¶2-3`, so the reviewed Book II set now covers the full MVP graph.
- 2026-04-11: Make `data/processed/` the canonical public reviewed export and treat candidate
  files as maintainer-only workflow material rather than a second public app mode.
- 2026-04-11: Replace the public review-mode toggle with a single reviewed Book II app surface,
  add a `Home` page, and move technical metadata behind optional detail sections.
- 2026-04-11: Add a small Streamlit v2 graph bridge around the existing PyVis HTML so clicking a
  node in the overall map or the local concept map opens that concept in Concept Explorer.
- 2026-04-11: Add an in-app reviewed dataset download bundle and document Books III, IV, VI, and
  X as the next corpus-expansion roadmap rather than extending scope in this batch.
- 2026-04-11: Clarify the post-Book II roadmap around Books III, IV, VI, and X specifically,
  because those books would turn the project from a strong Book II explorer into a more complete
  companion for students, reading groups, self-directed readers, and structured-dataset work.
- 2026-04-11: Merge the ego graph into Concept Explorer and remove the separate `Graph View`, so
  narrative context, evidence links, and local structure stay on one page during close reading.

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
- `docs/assets/aristotle-head-icon.png`
- `docs/viewer_guide.md`
- `docs/deployment.md`
- `LICENSE`
- `streamlit_app.py`
- `requirements.txt`
- `.streamlit/config.toml`
- `src/aristotle_graph/viewer/`
- `src/aristotle_graph/app/streamlit_app.py`

Observed results:

- Book II normalizes to 9 sections
- the canonical interim export contains 45 passages
- repeated segmentation runs produced the same SHA-256 for
  `data/interim/book2_passages.jsonl`
- candidate annotation validation currently exports 54 concepts and 42 relations
- strict approved mode now validates and exports the full reviewed Book II set of 54 concepts and
  42 relations
- processed passage export now carries all 45 authoritative Book II passages in both candidate
  and approved modes
- GraphML export loads successfully as a flattened representation of the processed graph
- the local Streamlit app launches successfully and now centers on a reviewed-only Book II
  dataset with `Home`, concept, passage, overall-map, and stats views
- the local Streamlit app now also includes an interactive `Overall Map` page that renders the
  full filtered Book II network with kind colors, built-in graph menus, and hub summaries
- the overall map and the embedded concept map now support node click-through into Concept
  Explorer through a small Streamlit v2 component bridge over the PyVis HTML
- the small ego graph now lives inside Concept Explorer, so the default concept-reading page
  includes its own local navigation surface without forcing a separate view change
- Concept Explorer now leads with a deterministic plain-language summary and passage previews,
  while ids, tiers, and tables sit behind optional detail sections
- Passage Explorer is now easier to enter from `Home`, concept evidence cards, and relation cards,
  and it supports concept jump-backs from linked passage concepts
- the public app now includes a one-click reviewed dataset download bundle built from the
  processed JSONL, JSON, GraphML, and stats exports
- the README now leads with the actual Book II findings and the practical value of the graph,
  rather than only describing the toolchain
- the public-facing repo now includes a real viewer preview, a compact overview graphic, a
  viewer guide, and a code license
- the public-facing repo and live app now share a small Aristotle head PNG, which makes the
  project easier to recognize without replacing the dashboard screenshot as the main entry point
- the repository is now deployment-ready for Streamlit Community Cloud with a root app
  entrypoint and explicit deployment instructions
- the README top section now centers on a single dashboard hero, a non-misleading live-status
  CTA, and a lighter first-run path that does not force export commands before opening the app
- the public README now points directly to the live Streamlit dashboard at
  `https://aristotle-virtue-graph.streamlit.app/`
- the viewer now includes curated `Start here` shortcuts and one-click passage jumps from
  concept evidence and relation shortcuts into Passage Explorer
- the one-click passage jumps now work on Streamlit Community Cloud without raising a
  session-state mutation exception
- the passage-jump buttons now use callback-driven queued navigation, which is more robust across
  local Streamlit and Community Cloud runs
- the reviewed Book II graph now includes 54 concepts and 42 relations, covering all nine
  section-7 virtue clusters in this MVP
- the project now lives in its own public GitHub repository rather than remaining nested inside
  the unrelated parent `MESOTES` repository
- `pytest`, `ruff check .`, and `mypy src/` all pass

Known limitations:

- Bekker references and CTS URNs are not yet populated
- GraphML intentionally flattens nested structures, so `book2_graph.json` remains the richer
  downstream format
- the live Streamlit URL is now the shorter custom subdomain
  `https://aristotle-virtue-graph.streamlit.app/`
- the current scope is still Book II only, so users who want the full treatment of courage,
  temperance, practical wisdom, or happiness still need later books

Next recommended step:

- expand next into Books III, IV, VI, and X, in that order, while preserving the same reviewed,
  passage-grounded discipline; that sequence would complete the Book II treatment of courage and
  temperance, deepen the practical virtue triads, add practical wisdom as the governing hinge,
  and connect the graph back to happiness and the good life
