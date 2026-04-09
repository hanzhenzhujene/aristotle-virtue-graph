# Annotation Guide

Milestone 2 introduces a candidate-versus-approved annotation workflow for Book II.

## Non-negotiable rules

- every concept must point to at least one passage
- every relation must point to at least one passage
- every relation endpoint must refer to an existing concept
- the sole passage authority is `data/interim/book2_passages.jsonl`
- candidate material must not be treated as final ground truth

## File layout

Book II annotations live in:

- `annotations/book2/concepts.candidate.yaml`
- `annotations/book2/relations.candidate.yaml`
- `annotations/book2/concepts.approved.yaml`
- `annotations/book2/relations.approved.yaml`

## Labeling guidance

- Preserve Ross wording in `source_labels`.
- Use `aliases` for modernized classroom labels or editorial shorthand.
- Keep concept ids stable even if labels change later.
- Do not silently replace source wording with modern paraphrase.

## Assertion tiers

Use `assertion_tier` carefully:

- `textual`: the claim is directly grounded in the wording of Book II
- `editorial_normalization`: the repo is normalizing wording for stable graph use
- `interpretive`: the repo is making a stronger synthesis or interpretation

Prefer `textual` where possible.
Use `editorial_normalization` when the id or domain label is cleaner than Ross's surface form.
Avoid speculative `interpretive` additions in this milestone.

## Review workflow

1. Validate the candidate files:
   - `python -m aristotle_graph.cli annotations validate`
2. Inspect the cited passages for the item you want to promote.
3. Move the item into the matching `*.approved.yaml` file.
4. Change `review_status` from `candidate` to `approved`.
5. Remove the candidate copy.
6. Validate strict mode:
   - `python -m aristotle_graph.cli annotations validate --strict-approved`
7. Export strict processed outputs if needed:
   - `python -m aristotle_graph.cli annotations export-all --strict-approved --output-dir data/processed/approved`

## Processed outputs and viewer modes

Candidate export writes processed files to `data/processed/`.
Strict approved export should usually write to `data/processed/approved/`.

The local Streamlit viewer reads those processed artifacts directly:

- `candidate` mode loads `data/processed/`
- `approved` mode loads `data/processed/approved/`

The approved pathway is intentionally conservative.
If no reviewed subset has been promoted yet, approved mode should show an explanatory empty
state instead of treating candidate material as final.

This repository now includes a small reviewed Book II core, so strict mode and approved-mode
viewing are usable immediately.

## Export outputs

Candidate export writes:

- `data/processed/book2_passages.jsonl`
- `data/processed/book2_concepts.jsonl`
- `data/processed/book2_relations.jsonl`
- `data/processed/book2_graph.json`
- `data/processed/book2_graph.graphml`
- `data/processed/book2_stats.json`

Strict approved export writes the same filenames to the chosen output directory.

## Promotion guidance

When promoting an item:

- keep the stable `id` unchanged
- preserve Ross wording in `source_labels`
- keep modernized labels in `aliases` only
- verify every cited `passage_id` against `data/interim/book2_passages.jsonl`
- ensure any approved relation points only to approved concepts before strict export
