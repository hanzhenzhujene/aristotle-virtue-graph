from __future__ import annotations

import argparse

from ethics_prompt_rewrite.config import load_config
from ethics_prompt_rewrite.pipeline import run_single_seed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    run_single_seed(config, seed=config.experiment.seed, smoke=True)


if __name__ == "__main__":
    main()
