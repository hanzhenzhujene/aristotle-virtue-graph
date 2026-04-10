from __future__ import annotations

from pathlib import Path
from typing import Any

from ethics_prompt_rewrite.utils import read_json, utc_now_iso, write_json

DEFAULT_STATE: dict[str, Any] = {
    "current_phase": "initialized",
    "adaptation_complete": False,
    "final_test_unlocked": False,
    "final_test_evaluated": False,
    "updated_at": None,
}


def state_path(run_root: Path) -> Path:
    return run_root / "state.json"


def load_state(run_root: Path) -> dict[str, Any]:
    path = state_path(run_root)
    if not path.exists():
        return dict(DEFAULT_STATE)
    raw = read_json(path)
    state = dict(DEFAULT_STATE)
    state.update(raw)
    return state


def update_state(run_root: Path, **changes: Any) -> dict[str, Any]:
    state = load_state(run_root)
    state.update(changes)
    state["updated_at"] = utc_now_iso()
    write_json(state_path(run_root), state)
    return state
