# Data Model

The repository builds a passage-grounded graph for *Nicomachean Ethics* Book II.
The model is layered:

- authoritative passage records
- annotation records for concepts and relations
- processed exports for graph building and local viewing

## Passage authority

The sole passage authority for annotation and export is:

- `data/interim/book2_passages.jsonl`

Concepts and relations may only cite passage ids from that file.

Milestone 3 also writes processed passage exports for downstream tools:

- `data/processed/book2_passages.jsonl`
- `data/processed/approved/book2_passages.jsonl`

Processed passage files are derived from the authoritative interim export. They do not create
new passage ids.

Each passage row includes:

- `passage_id`
- `work_id`
- `book_number`
- `chapter_or_section`
- `sequence_in_book`
- `source_id`
- `source_url`
- `citation_label`
- `text`
- optional `cts_urn`
- optional `bekker_ref`
- `char_count`
- `hash`

## Layering rule

The graph keeps three claim layers distinct:

- `textual`
- `editorial_normalization`
- `interpretive`

These appear as `assertion_tier` on both concepts and relations and are preserved through
processed export.

## Evidence object

Each evidence record contains:

- `passage_id`
- `support_type`
- `note`
- optional `quote_excerpt`

`support_type` is one of:

- `direct`
- `paraphrase`
- `editorial`

Evidence objects are embedded inside concepts and relations.
Every concept and every relation must carry at least one evidence object.

## Concept object

Each concept contains:

- stable `id`
- `primary_label`
- `source_labels`
- optional `aliases`
- `kind`
- `description`
- `assertion_tier`
- `book`
- `sections`
- non-empty `evidence`
- `review_status`
- optional `notes`

The current concept kinds are intentionally small:

- `virtue`
- `vice`
- `domain`
- `principle`
- `state`
- `faculty`
- `passion`
- `process`
- `action`
- `person`
- `condition`

## Relation object

Each relation contains:

- stable `id`
- `source_id`
- `relation_type`
- `target_id`
- `assertion_tier`
- non-empty `evidence`
- `review_status`
- optional `notes`

The relation vocabulary is deliberately narrow:

- `is_a`
- `formed_by`
- `concerns`
- `requires`
- `determined_by`
- `relative_to`
- `has_excess`
- `has_deficiency`
- `opposed_to`
- `contrasted_with`

Every relation endpoint must resolve to an existing concept id.

## Review status

Annotations are stored in one of two states:

- `candidate`
- `approved`

Candidate mode exports all validated annotations.
Strict approved mode exports only approved annotations and fails if approved relations point to
candidate-only concepts.

The local viewer supports both modes:

- `candidate` reads `data/processed/`
- `approved` reads `data/processed/approved/`

If the approved subset has zero concepts and zero relations, the viewer shows an explicit
empty-state notice instead of failing.

## Processed graph exports

Milestone 3 writes these downstream artifacts:

- `data/processed/book2_graph.json`
- `data/processed/book2_graph.graphml`
- `data/processed/book2_stats.json`

The primary rich export is `book2_graph.json`.
It uses a simple node-link shape:

- `meta`: book number, export mode, and top-level counts
- `nodes`: concept rows enriched for graph use
- `edges`: relation rows enriched for graph use
- `passages`: passage rows for evidence lookup

The local viewer reads the processed JSON artifacts directly.

## GraphML flattening

GraphML is an interoperability export, not the canonical rich format.

GraphML-safe attributes are exported directly.
Lists and nested structures are flattened predictably into string fields, such as:

- `source_labels_json`
- `aliases_json`
- `sections_json`
- `evidence_passage_ids_json`
- `evidence_support_types_json`
- `evidence_notes_json`

Important information is flattened rather than silently discarded.
