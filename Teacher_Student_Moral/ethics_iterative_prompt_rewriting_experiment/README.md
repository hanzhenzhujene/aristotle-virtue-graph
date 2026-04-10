# Ethics Iterative Prompt Rewriting Experiment

This project tests whether a strong Gemini teacher can improve a local Qwen-0.5B student on the ETHICS commonsense benchmark through prompt rewriting alone.

## Guarantees

- The student is local only.
- The default local student backend in the provided configs is Apple-native MLX (`mlx-community/Qwen2.5-0.5B-Instruct-4bit`).
- The final test split is isolated and locked until final evaluation.
- The teacher only edits the mutable prompt slot.
- No fine-tuning, retrieval augmentation, or hidden training is used.
- Teacher calls are cached and schema-validated for resume safety.

## Project Layout

- `configs/`: YAML experiment configs.
- `docs/execplans/`: execution plan for this research build.
- `prompts/`: teacher prompt templates.
- `scripts/`: runnable entrypoints.
- `src/ethics_prompt_rewrite/`: experiment package.
- `tests/`: unit tests for split integrity and parsing.
- `outputs/`: generated artifacts, caches, and metrics.
- `reports/`: markdown and figure reports.

## Quick Start

1. Create and activate a virtual environment inside this folder.
2. Install the package with `pip install -e ".[dev]"`.
3. Export `GEMINI_API_KEY`.
4. Run a smoke test with `python scripts/run_smoke.py --config configs/smoke.yaml`.
5. Run one full seed with `python scripts/run_experiment.py --config configs/base.yaml --seed 17`.
6. Generate or refresh the top-level report with `python scripts/generate_report.py --config configs/base.yaml --run-roots outputs/runs/seed_17`.
7. Attempt multi-seed execution with `python scripts/run_multiseed.py --config configs/base.yaml`.

## Outputs

Each seed writes a self-contained run directory under `outputs/runs/seed_<seed>/` containing:

- split manifests and duplicate-group audit files
- prompt versions and teacher JSON responses
- selector-dev and final-test predictions
- metrics, statistical tests, and confidence intervals
- a resume-safe run state

The final report is written to `reports/final_report.md`.

## Notes

- Historical partial runs from slower backends may be preserved under sibling names such as `outputs/runs/seed_17_hf_partial/` for traceability.
- The base config is set up for the local MLX student backend because the original Transformers + MPS path was too slow for a practical full-seed run on this machine.
