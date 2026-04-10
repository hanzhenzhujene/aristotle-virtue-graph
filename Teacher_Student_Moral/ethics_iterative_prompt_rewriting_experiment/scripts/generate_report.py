from __future__ import annotations

import argparse
from pathlib import Path

from ethics_prompt_rewrite.config import load_config
from ethics_prompt_rewrite.reporting import generate_final_report
from ethics_prompt_rewrite.utils import read_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--run-roots", nargs="+", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    summaries = [
        read_json(Path(path) / "final_evaluation" / "statistics.json") for path in args.run_roots
    ]
    generate_final_report(
        config=config,
        project_root=config.project_root,
        seed_summaries=summaries,
        run_roots=[Path(path) for path in args.run_roots],
    )


if __name__ == "__main__":
    main()
