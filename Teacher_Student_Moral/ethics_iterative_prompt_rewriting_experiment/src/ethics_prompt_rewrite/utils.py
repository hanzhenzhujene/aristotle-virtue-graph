from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import subprocess
import sys
import unicodedata
from collections.abc import Iterable, Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

import numpy as np

T = TypeVar("T")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def normalize_text(text: str, *, casefold: bool = True) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    collapsed = " ".join(normalized.split())
    return collapsed.casefold() if casefold else collapsed


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(data: Any) -> str:
    return sha256_text(json.dumps(data, sort_keys=True, ensure_ascii=False))


def write_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def chunked(items: Sequence[T], size: int) -> Iterator[list[T]]:
    for start in range(0, len(items), size):
        yield list(items[start : start + size])


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def set_global_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


def sliding_average(values: Sequence[float], window: int) -> list[float]:
    result: list[float] = []
    for index in range(len(values)):
        start = max(0, index + 1 - window)
        view = values[start : index + 1]
        result.append(float(sum(view) / len(view)))
    return result


def describe_environment() -> dict[str, Any]:
    try:
        freeze = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    except Exception as exc:  # pragma: no cover
        freeze = [f"pip freeze failed: {exc}"]

    return {
        "python_version": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "package_versions": freeze,
    }
