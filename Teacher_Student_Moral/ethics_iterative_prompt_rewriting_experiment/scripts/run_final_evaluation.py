from __future__ import annotations

import argparse

from ethics_prompt_rewrite.config import load_config
from ethics_prompt_rewrite.data import LockedSplitStore, load_label_semantics
from ethics_prompt_rewrite.evaluation import run_final_evaluation
from ethics_prompt_rewrite.pipeline import run_root_for_seed
from ethics_prompt_rewrite.student import build_student_backend
from ethics_prompt_rewrite.utils import read_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    run_root = run_root_for_seed(config, args.seed, smoke=args.smoke)
    final_prompts = read_json(run_root / "final_prompts.json")
    store = LockedSplitStore(run_root)
    student = build_student_backend(config)
    label_semantics = load_label_semantics(run_root)
    run_final_evaluation(
        config=config,
        run_root=run_root,
        store=store,
        student=student,
        label_semantics=label_semantics,
        final_prompts=final_prompts,
    )


if __name__ == "__main__":
    main()
