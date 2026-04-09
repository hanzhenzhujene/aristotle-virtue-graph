# Book II Annotations

This directory holds the Milestone 2 annotation layer for *Nicomachean Ethics* Book II.

## Authority

The sole passage authority for this milestone is:

- `data/interim/book2_passages.jsonl`

Every concept and every relation must point to one or more passage ids from that file.

## Files

- `concepts.candidate.yaml`: machine-assisted or editor-drafted candidates that still require
  human review
- `relations.candidate.yaml`: machine-assisted or editor-drafted candidate relations
- `concepts.approved.yaml`: human-reviewed concepts only
- `relations.approved.yaml`: human-reviewed relations only

Candidates and approved items are intentionally separated. Duplicate ids across files are
rejected.

The repository currently includes a reviewed core subset in the approved files. That subset
covers sections 1, 4, 5, 6, and the courage and temperance triads from section 7.

## Review policy

- All model-generated annotations must start as `review_status: candidate`.
- Only human-reviewed items belong in the `*.approved.yaml` files.
- Strict export mode reads only approved items.
- Approved relations must point only to approved concepts in strict mode.

## Promotion workflow

1. Inspect a candidate item against the passage ids listed in its `evidence`.
2. Confirm that the `primary_label`, `source_labels`, `assertion_tier`, and relation direction
   are appropriate for Book II.
3. Move the item from the candidate file into the matching approved file.
4. Change `review_status` from `candidate` to `approved`.
5. Remove the old candidate copy. The validator rejects duplicate ids.
6. Run:
   - `python -m aristotle_graph.cli annotations validate`
   - `python -m aristotle_graph.cli annotations validate --strict-approved`

## Annotation philosophy

- Preserve Ross wording in `source_labels`.
- Use `aliases` only for modernized or editorially normalized labels.
- Keep `assertion_tier` explicit:
  - `textual`
  - `editorial_normalization`
  - `interpretive`
- Prefer fewer, better-supported concepts over speculative over-annotation.
- Do not expand beyond Book II in this directory.
