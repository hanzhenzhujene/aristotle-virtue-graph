# Annotation Guide

The public app now exposes a full reviewed Book II graph and a separate reviewed Book III starter.
This guide is therefore maintainer-facing: it explains how new work begins in candidate files
without leaking draft material into the public dashboard.

## Non-negotiable rules

- every concept must point to at least one passage
- every relation must point to at least one passage
- every relation endpoint must refer to an existing concept
- the sole passage authority for any annotation bundle is its matching interim passage file
  such as `data/interim/book2_passages.jsonl` or `data/interim/book3_passages.jsonl`
- candidate material must not be treated as final ground truth

## File layout

Book II annotations live in:

- `annotations/book2/concepts.candidate.yaml`
- `annotations/book2/relations.candidate.yaml`
- `annotations/book2/concepts.approved.yaml`
- `annotations/book2/relations.approved.yaml`

The approved files now contain the full public Book II set.
The candidate files are intentionally empty templates at the moment.

Book III annotations now live in:

- `annotations/book3/concepts.candidate.yaml`
- `annotations/book3/relations.candidate.yaml`
- `annotations/book3/concepts.approved.yaml`
- `annotations/book3/relations.approved.yaml`

The current Book III reviewed starter is intentionally narrower than Book II.
It covers:

- voluntary and involuntary action
- choice and deliberation
- courage
- temperance

The Book III candidate layer currently keeps one explicit normalization unresolved:
the deficiency on the temperance side, which Book III says has no settled name.

## Labeling guidance

- Preserve Ross wording in `source_labels`.
- Use `aliases` for modernized classroom labels or editorial shorthand.
- Keep concept ids stable even if labels change later.
- Do not silently replace source wording with modern paraphrase.

## Assertion tiers

Use `assertion_tier` carefully:

- `textual`: the claim is directly grounded in the wording of the relevant book
- `editorial_normalization`: the repo is normalizing wording for stable graph use
- `interpretive`: the repo is making a stronger synthesis or interpretation

Prefer `textual` where possible.
Use `editorial_normalization` when the id or domain label is cleaner than Ross's surface form.
Avoid speculative `interpretive` additions.

## Review workflow

1. Draft new items in the candidate files.
2. Validate the draft layer:
   - `python -m aristotle_graph.cli annotations validate --book N`
3. Inspect the cited passages for every item you want to promote.
4. Move the reviewed items into the matching `*.approved.yaml` file.
5. Change `review_status` from `candidate` to `approved`.
6. Remove the candidate copy.
7. Validate strict mode:
   - `python -m aristotle_graph.cli annotations validate --book N --strict-approved`
8. Rebuild the reviewed exports:
   - `python -m aristotle_graph.cli annotations export-all --book N --strict-approved`

If you want a separate strict-approved compatibility copy as well:

- `python -m aristotle_graph.cli annotations export-all --book N --strict-approved --output-dir ...`

## Public versus maintainer data surfaces

The public app reads:

- `data/processed/book2_passages.jsonl`
- `data/processed/book2_concepts.jsonl`
- `data/processed/book2_relations.jsonl`
- `data/processed/book2_graph.json`
- `data/processed/book2_graph.graphml`
- `data/processed/book2_stats.json`

Those files are now reviewed-only exports.

The repository also now contains a reviewed Book III starter export in:

- `data/processed/book3_passages.jsonl`
- `data/processed/book3_concepts.jsonl`
- `data/processed/book3_relations.jsonl`
- `data/processed/book3_graph.json`
- `data/processed/book3_graph.graphml`
- `data/processed/book3_stats.json`

Those Book III exports are for maintainer and downstream graph work at this stage.
They do not yet power the live dashboard.

Candidate material is for maintainers.
If a future workflow needs a draft export for internal review, produce it deliberately with the
CLI rather than surfacing it in the public app by default.

## Promotion guidance

When promoting an item:

- keep the stable `id` unchanged
- preserve Ross wording in `source_labels`
- keep modernized labels in `aliases` only
- verify every cited `passage_id` against the relevant `data/interim/bookN_passages.jsonl`
- ensure any approved relation points only to approved concepts before strict export
