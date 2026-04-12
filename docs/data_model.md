# Data Model

The repository now has:

- a public reviewed Book II dataset that powers the live dashboard
- a reviewed Book III starter slice committed for downstream graph work

The model is layered:

- authoritative passage records
- annotation records for concepts and relations
- processed exports for graph building, app loading, and dataset download

## Passage authority

The passage authority is book-specific.
Current authoritative interim files are:

- `data/interim/book2_passages.jsonl`
- `data/interim/book3_passages.jsonl`

Concepts and relations may only cite passage ids from the matching book authority file.

Processed passage files are derived from the authoritative interim export.
They do not create new passage ids.

The current reviewed processed exports live at:

- `data/processed/book2_passages.jsonl`
- `data/processed/book3_passages.jsonl`

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

Annotations are still stored in two states:

- `candidate`
- `approved`

But the public app now runs only on the reviewed Book II export.
Candidate files remain for maintainer workflow when future additions are drafted and checked.
Book III currently uses the same candidate-versus-approved discipline, but only its reviewed
starter export is committed into `data/processed/`.

## Processed graph exports

Reviewed artifacts live in `data/processed/` on a per-book basis.
Current committed sets are:

- `data/processed/book2_passages.jsonl`
- `data/processed/book2_concepts.jsonl`
- `data/processed/book2_relations.jsonl`
- `data/processed/book2_graph.json`
- `data/processed/book2_graph.graphml`
- `data/processed/book2_stats.json`
- `data/processed/book3_passages.jsonl`
- `data/processed/book3_concepts.jsonl`
- `data/processed/book3_relations.jsonl`
- `data/processed/book3_graph.json`
- `data/processed/book3_graph.graphml`
- `data/processed/book3_stats.json`

Each `bookN_graph.json` file is the primary rich export.
It uses a simple node-link shape:

- `meta`: book number, export mode, and top-level counts
- `nodes`: concept rows enriched for graph use
- `edges`: relation rows enriched for graph use
- `passages`: passage rows for evidence lookup

The local viewer and the in-app download bundle currently read the Book II reviewed artifacts
directly.

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
