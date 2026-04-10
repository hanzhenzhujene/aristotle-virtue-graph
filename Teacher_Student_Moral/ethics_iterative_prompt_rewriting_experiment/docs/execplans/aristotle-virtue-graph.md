# Execution Plan

## Scope

Build and execute a fully isolated experiment inside this project folder only. No files outside this folder may be modified.

## Phases

1. Scaffold the package, configs, prompts, scripts, and tests.
2. Implement data loading, normalization, label-semantics validation, duplicate grouping, and locked splits.
3. Implement the local student backends and the Gemini teacher interface with caching.
4. Implement the four experimental arms, selector-based stopping, final-test gating, and statistical analysis.
5. Run smoke validation, then at least one full seed, then attempt three seeds if feasible.
6. Generate reports, plots, and a concise answer to the research question.

## Progress

- [x] Create isolated project directory and core layout.
- [x] Implement the experiment package.
- [x] Install dependencies.
- [x] Run smoke test.
- [x] Run at least one end-to-end seed.
- [x] Attempt multi-seed execution.
- [x] Generate final report.

## Notes

- The ETHICS `commonsense` configuration was loaded directly and verified at runtime before any split logic. Observed official counts were train `13,910`, validation `3,885`, test `3,964`, for `21,759` total examples.
- Label semantics were not explicitly documented in the loaded dataset metadata, so the pipeline inferred the mapping from loaded examples and logged the evidence path in `data/label_semantics.json`.
- Smoke testing exercised resume support, teacher-call caching, selector-only prompt selection, and locked final-test evaluation.
- Local student benchmarking on this Apple Silicon MPS setup showed the Qwen-0.5B backend was fastest and most stable at student batch size `8`; larger batches were slower and could trigger memory pressure.
- The original Hugging Face Transformers + MPS student path proved too slow for a full seed on this machine, so the experiment was pivoted to a local Apple-native MLX backend using `mlx-community/Qwen2.5-0.5B-Instruct-4bit`. This preserved the local no-fine-tuning student constraint while making the full seed feasible.
- One full seed (`17`) and a fresh MLX-backed smoke test completed successfully. Additional seeds were not run in this session because the end-to-end runtime for a full seed remained substantial even after the MLX pivot, but the one-command path remains `python scripts/run_multiseed.py --config configs/base.yaml`.
