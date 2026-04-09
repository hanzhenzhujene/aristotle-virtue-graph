PYTHON ?= python3

.PHONY: install sources fetch normalize segment annotations-validate annotations-validate-strict annotations-export annotations-export-strict annotations-stats app test lint typecheck check

install:
	$(PYTHON) -m pip install -e ".[dev,viewer]"

sources:
	$(PYTHON) -m aristotle_graph.cli sources list

fetch:
	$(PYTHON) -m aristotle_graph.cli fetch --source wikisource_ross_1908 --book 2

normalize:
	$(PYTHON) -m aristotle_graph.cli normalize --source wikisource_ross_1908 --book 2

segment:
	$(PYTHON) -m aristotle_graph.cli segment --source wikisource_ross_1908 --book 2

annotations-validate:
	$(PYTHON) -m aristotle_graph.cli annotations validate

annotations-validate-strict:
	$(PYTHON) -m aristotle_graph.cli annotations validate --strict-approved

annotations-export:
	$(PYTHON) -m aristotle_graph.cli annotations export-all

annotations-export-strict:
	$(PYTHON) -m aristotle_graph.cli annotations export-all --strict-approved --output-dir data/processed/approved

annotations-stats:
	$(PYTHON) -m aristotle_graph.cli annotations stats

app:
	$(PYTHON) -m streamlit run streamlit_app.py

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy src/

check: test lint typecheck
