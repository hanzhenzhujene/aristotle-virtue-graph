from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    data_dir: Path
    raw_dir: Path
    interim_dir: Path
    processed_dir: Path
    annotations_dir: Path
    schema_dir: Path
    user_agent: str
    timeout_seconds: float = 30.0


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    repo_root = get_repo_root()
    data_dir = repo_root / "data"
    return Settings(
        repo_root=repo_root,
        data_dir=data_dir,
        raw_dir=data_dir / "raw",
        interim_dir=data_dir / "interim",
        processed_dir=data_dir / "processed",
        annotations_dir=repo_root / "annotations",
        schema_dir=repo_root / "schemas",
        user_agent=os.getenv(
            "ARISTOTLE_GRAPH_USER_AGENT",
            "AristotleVirtueGraph/0.1 (+https://example.invalid/local)",
        ),
    )


def ensure_project_directories() -> None:
    settings = get_settings()
    for path in (
        settings.data_dir,
        settings.raw_dir,
        settings.interim_dir,
        settings.processed_dir,
        settings.annotations_dir,
        settings.schema_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
