from __future__ import annotations

import pytest

from ethics_prompt_rewrite.teacher import _coerce_teacher_response, _extract_json_payload


def test_extract_json_payload_recovers_from_wrapped_text() -> None:
    payload = _extract_json_payload(
        "```json\n"
        '{"diagnosis_summary":"brief","failure_modes":[],"change_summary":[],'
        '"revised_prompt":"Be careful."}\n'
        "```"
    )
    assert payload["diagnosis_summary"] == "brief"


def test_coerce_teacher_response_accepts_string_summaries() -> None:
    response = _coerce_teacher_response(
        {
            "diagnosis_summary": "The model misses coercion.",
            "failure_modes": "coercion\nprivacy",
            "change_summary": "stress coercion;stress privacy",
            "revised_prompt": (
                "Judge the action as written and watch for coercion or privacy violations."
            ),
        }
    )
    assert response.failure_modes == ["coercion", "privacy"]
    assert response.change_summary == ["stress coercion", "stress privacy"]


def test_coerce_teacher_response_requires_revised_prompt() -> None:
    with pytest.raises(RuntimeError, match="revised_prompt"):
        _coerce_teacher_response(
            {
                "diagnosis_summary": "brief",
                "failure_modes": [],
                "change_summary": [],
                "revised_prompt": "  ",
            }
        )
