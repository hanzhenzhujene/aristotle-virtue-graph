# Aristotle Virtue Graph agent guide

## Purpose

This repository builds an evidence-first knowledge graph for Aristotle's virtue ethics,
starting with *Nicomachean Ethics* Book II.

## Working mode

For any non-trivial feature, use the execution plan in
`docs/execplans/aristotle-virtue-graph.md`.
Keep that file updated as work progresses.
Do not expand scope beyond Book II unless the user explicitly asks.

## Project rules

- Every concept and every non-hierarchical relation must have passage evidence.
- Separate explicit textual claims from editorial normalization and interpretation.
- Do not treat LLM-generated outputs as ground truth.
- Prefer simple local files over external services or databases.
- Prefer Python standard library plus a small number of well-justified dependencies.
- Keep IDs stable once exported.
- If source licensing is unclear, do not commit raw source text; commit download scripts or
  derived structured data instead.

## Repo expectations

- Core package lives in `src/aristotle_graph/`.
- Human-reviewed annotations live in `annotations/`.
- Processed exports live in `data/processed/`.
- Project docs live in `docs/`.
- Tests live in `tests/`.

## Commands to keep working

- Install: `pip install -e ".[dev,viewer]"`
- Test: `pytest`
- Lint: `ruff check .`
- Type check: `mypy src/`
- Run app: `python -m streamlit run streamlit_app.py`

## Done means

A task is not done until:

- relevant tests pass
- lint passes
- docs are updated if behavior or schema changed
- the execution plan is updated if the task was multi-step
