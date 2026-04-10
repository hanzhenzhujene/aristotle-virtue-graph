from __future__ import annotations

import argparse

from ethics_prompt_rewrite.config import load_config
from ethics_prompt_rewrite.data import prepare_dataset
from ethics_prompt_rewrite.pipeline import run_root_for_seed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    run_root = run_root_for_seed(config, args.seed, smoke=args.smoke)
    prepare_dataset(config, seed=args.seed, run_root=run_root)


if __name__ == "__main__":
    main()
