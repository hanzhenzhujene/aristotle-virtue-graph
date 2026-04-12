# Book III annotations

This directory starts the Book III annotation tranche without changing the public Book II app.

Current reviewed scope:

- voluntary and involuntary action
- choice, deliberation, wish, ends, and means
- courage, rashness, cowardice, and fear/confidence
- temperance, self-indulgence, and bodily pleasures

Current candidate-only material:

- the temperance-side deficiency that Book III says has no settled name

Why the candidate layer is still needed here:

- Book III sometimes revisits a Book II structure without repeating the same label
- the clearest example is the deficient counterpart to temperance:
  Book II names `insensibility`, but Book III.11 says the type "has not received a name"
- that normalization can be proposed in candidate form, but it should not become reviewed
  Book III data until a maintainer explicitly approves the carry-over

Validation flow:

- candidate + approved together:
  `python -m aristotle_graph.cli annotations validate --book 3`
- reviewed subset only:
  `python -m aristotle_graph.cli annotations validate --book 3 --strict-approved`
- reviewed exports:
  `python -m aristotle_graph.cli annotations export-all --book 3 --strict-approved`

Passage authority:

- `data/interim/book3_passages.jsonl`
