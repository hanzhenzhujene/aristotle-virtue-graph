# Viewer Guide

The local viewer is the fastest way to understand what this repository is doing.

## Start here

If you only want to open the viewer against the committed Book II exports:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[viewer]"
make app
```

If you also want to rebuild the processed exports first:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev,viewer]"
make annotations-export
make annotations-export-strict
python -m streamlit run streamlit_app.py
```

Once the app opens, start with `courage`.

The sidebar now includes a small `Start here` set so you can jump straight to a few strong entry
points without typing.

## Suggested first walkthrough

1. Stay in `candidate` mode and choose `courage`.
2. Read the outgoing relations:
   - `has_excess -> rashness`
   - `has_deficiency -> cowardice`
   - `concerns -> fear and confidence`
3. Use the evidence shortcut to open the linked passage `NE II.7 ¶1`.
4. Switch to `approved` mode and compare the reviewed subset against the larger candidate map.

This is the quickest way to see how the project works:
graph claims stay connected to the text.

## What each view is for

### Concept Explorer

Use this when you want to understand one concept well.

It shows:

- labels and aliases
- kind and assertion tier
- review status
- supporting evidence
- incoming and outgoing relations
- one-click shortcuts that open the relevant passage in Passage Explorer

### Passage Explorer

Use this when you want to start from the text.

It shows:

- the full passage text
- linked concepts
- linked relations

### Graph View

Use this when you want a local structural view without rendering the entire graph as a hairball.

The graph view centers on one concept and expands to a 1-hop or 2-hop neighborhood.

### Overall Map

Use this when you want the whole filtered Book II network in one place.

It shows:

- the full filtered node-edge map, not just one ego neighborhood
- built-in graph menus for search and kind-based filtering inside the canvas
- optional edge labels for a denser explanatory view
- top connected concepts and the current relation mix
- isolated nodes that still match your current sidebar filters

### Stats

Use this for a quick sense of scale:

- concept counts
- relation counts
- passage counts
- kind and relation-type breakdowns
- review-status breakdowns

## Candidate vs approved

- `candidate` mode shows the broader working layer
- `approved` mode shows only the reviewed subset

The difference matters.
The project is designed so tentative structure and reviewed structure remain visibly distinct.

## What to look for

The viewer is most useful when you ask concrete questions such as:

- What exactly does Book II connect courage to?
- Which relations are reviewed and which are still tentative?
- Where is this claim grounded in the passage sequence?
- Is this node a direct textual claim or an editorial normalization?
