# Book II Annotations

This directory holds the human-reviewed annotation source for *Nicomachean Ethics* Book II.

## Authority

The sole passage authority for annotation and export is:

- `data/interim/book2_passages.jsonl`

Every concept and every relation must point to one or more passage ids from that file.

## Files

- `concepts.approved.yaml`: the reviewed Book II concept set
- `relations.approved.yaml`: the reviewed Book II relation set
- `concepts.candidate.yaml`: maintainer-facing draft concepts, currently empty
- `relations.candidate.yaml`: maintainer-facing draft relations, currently empty

The public app and the committed processed dataset now use the fully reviewed Book II set.
Candidate files remain in the repository only so future additions can begin as drafts instead of
being treated as ground truth.

## Current reviewed coverage

The approved files now cover the full Book II MVP:

- structural concepts such as moral virtue, habituation, pleasure and pain, virtuous action,
  and the mean
- all nine Book II section-7 virtue clusters used in this repo:
  courage, temperance, liberality, magnificence, proper pride, good temper, truthfulness,
  wit, and friendliness

## Review policy

- All model-generated or editor-drafted additions must start as `review_status: candidate`.
- Only human-reviewed items belong in the `*.approved.yaml` files.
- Strict export mode reads only approved items.
- Approved relations must point only to approved concepts.

## Promotion workflow

1. Add the draft item to the matching `*.candidate.yaml` file.
2. Inspect the cited passages in `data/interim/book2_passages.jsonl`.
3. Confirm the `primary_label`, `source_labels`, `assertion_tier`, and relation direction.
4. Move the item into the matching `*.approved.yaml` file.
5. Change `review_status` from `candidate` to `approved`.
6. Remove the candidate copy. Duplicate ids are rejected.
7. Run:
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
