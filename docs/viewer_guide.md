# Viewer Guide

The local viewer is the fastest way to understand what this repository is for.
It now opens directly into the reviewed Book II dataset.

## Start here

If you only want to open the viewer against the committed exports:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[viewer]"
make app
```

If you want to rebuild the reviewed exports first:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev,viewer]"
make annotations-validate
make annotations-validate-strict
make annotations-export
make app
```

Once the app opens, start with `courage`.

## Suggested first walkthrough

1. Land on `Home`.
2. Open `courage`.
3. Read the short narrative summary at the top of Concept Explorer.
4. Open the linked supporting passage `NE II.7 ¶1`.
5. Use the small concept map on the same page, or switch to `Overall Map`, and click a nearby node to jump into its concept page.

This is the quickest way to see how the project works:
the graph is navigable, but every claim stays attached to the passage that supports it.

## What each view is for

### Home

Use this for the app's job statement and the fastest entry points.

It gives you:

- a short explanation of why the graph exists
- guided paths into `courage`, `moral virtue`, and a passage-first route
- a dataset chooser for the full bundle or any single processed file, with file sizes

### Concept Explorer

Use this when you want to understand one concept well.

It shows:

- a short human-readable description
- a deterministic summary of how that concept functions in Book II
- a compact clickable local graph around the selected concept
- optional horizontal edge labels on that compact map when you want them, without forcing them
  on by default
- readable relation cards with one-click concept and passage jumps
- supporting passage previews
- an optional `Dataset details` section for ids, tiers, and structured tables

### Passage Explorer

Use this when you want to start from the text.

It shows:

- the full passage text
- linked concepts as buttons back into Concept Explorer
- linked relations grounded in that passage

### Overall Map

Use this when you want the whole filtered Book II network in one place.

It shows:

- the full filtered node-edge map, not just one ego neighborhood
- built-in graph menus for search and kind-based filtering inside the canvas
- optional edge labels for a denser explanatory view
- top connected concepts and the current relation mix
- node click-through into Concept Explorer

### Stats

Use this for a quick sense of scale:

- concept counts
- relation counts
- passage counts
- kind and relation-type breakdowns
- assertion-tier breakdowns

## What to look for

The viewer is most useful when you ask concrete questions such as:

- What exactly does Book II connect courage to?
- Where is this claim grounded in the passage sequence?
- How does Aristotle move from moral virtue to habit, pleasure, pain, and the mean?
- Which concepts become clearer when you start from the passage instead of from the graph?
