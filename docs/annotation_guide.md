# Annotation Guide

The public app now runs on a fully reviewed Book II dataset.
This guide is therefore maintainer-facing: it explains how new work begins in candidate files
without leaking draft material into the public dashboard.

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

The approved files now contain the full public Book II set.
The candidate files are intentionally empty templates at the moment.

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
Avoid speculative `interpretive` additions.

## Review workflow

1. Draft new items in the candidate files.
2. Validate the draft layer:
   - `python -m aristotle_graph.cli annotations validate`
3. Inspect the cited passages for every item you want to promote.
4. Move the reviewed items into the matching `*.approved.yaml` file.
5. Change `review_status` from `candidate` to `approved`.
6. Remove the candidate copy.
7. Validate strict mode:
   - `python -m aristotle_graph.cli annotations validate --strict-approved`
8. Rebuild the public reviewed exports:
   - `make annotations-export`

If you want a separate strict-approved compatibility copy as well:

- `make annotations-export-strict`

## Public versus maintainer data surfaces

The public app reads:

- `data/processed/book2_passages.jsonl`
- `data/processed/book2_concepts.jsonl`
- `data/processed/book2_relations.jsonl`
- `data/processed/book2_graph.json`
- `data/processed/book2_graph.graphml`
- `data/processed/book2_stats.json`

Those files are now reviewed-only exports.

Candidate material is for maintainers.
If a future workflow needs a draft export for internal review, produce it deliberately with the
CLI rather than surfacing it in the public app by default.

## Promotion guidance

When promoting an item:

- keep the stable `id` unchanged
- preserve Ross wording in `source_labels`
- keep modernized labels in `aliases` only
- verify every cited `passage_id` against `data/interim/book2_passages.jsonl`
- ensure any approved relation points only to approved concepts before strict export
