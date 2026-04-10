from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from ethics_prompt_rewrite.config import ExperimentConfig
from ethics_prompt_rewrite.models import TeacherBatchExample, TeacherRevisionResponse
from ethics_prompt_rewrite.utils import normalize_text, read_json, sha256_json, write_json


def _load_teacher_template(project_root: Path) -> str:
    path = project_root / "prompts" / "teacher_revision_prompt.md"
    return path.read_text(encoding="utf-8")


def _ngram_set(text: str, n: int) -> set[str]:
    tokens = normalize_text(text).split()
    if len(tokens) < n:
        return set()
    return {" ".join(tokens[index : index + n]) for index in range(len(tokens) - n + 1)}


def _coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            text = item.strip() if isinstance(item, str) else str(item).strip()
            if text:
                items.append(text)
        return items
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        parts = [
            part.strip(" -*\t")
            for part in re.split(r"(?:\r?\n|;)", stripped)
            if part.strip(" -*\t")
        ]
        return parts or [stripped]
    text = str(value).strip()
    return [text] if text else []


def _coerce_required_string(value: Any, field_name: str) -> str:
    if isinstance(value, list):
        text = " ".join(str(item).strip() for item in value if str(item).strip())
    elif value is None:
        text = ""
    else:
        text = str(value).strip()
    if not text:
        msg = f"Teacher response is missing required field: {field_name}"
        raise RuntimeError(msg)
    return text


def _extract_json_payload(raw_text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            msg = f"Gemini returned invalid JSON: {raw_text[:500]}"
            raise json.JSONDecodeError(msg, raw_text, exc.pos) from exc
        candidate = raw_text[start : end + 1]
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as nested_exc:
            msg = f"Gemini returned invalid JSON: {raw_text[:500]}"
            raise json.JSONDecodeError(msg, raw_text, nested_exc.pos) from nested_exc
    if not isinstance(parsed, dict):
        msg = f"Gemini returned JSON of type {type(parsed).__name__}, expected an object."
        raise RuntimeError(msg)
    return parsed


def _coerce_teacher_response(payload: dict[str, Any]) -> TeacherRevisionResponse:
    normalized: dict[str, Any] = {
        "diagnosis_summary": _coerce_required_string(
            payload.get("diagnosis_summary"),
            "diagnosis_summary",
        ),
        "failure_modes": _coerce_string_list(payload.get("failure_modes")),
        "change_summary": _coerce_string_list(payload.get("change_summary")),
        "revised_prompt": _coerce_required_string(payload.get("revised_prompt"), "revised_prompt"),
    }
    return TeacherRevisionResponse(**normalized)


def validate_teacher_response(
    response: TeacherRevisionResponse,
    *,
    batch_examples: list[TeacherBatchExample],
    max_chars: int,
) -> None:
    revised = response.revised_prompt.strip()
    if len(revised) > max_chars:
        msg = f"Teacher prompt exceeded max length: {len(revised)} > {max_chars}"
        raise RuntimeError(msg)
    forbidden_terms = ("teacher_dev", "selector_dev", "chain-of-thought", "answer key")
    lowered = revised.lower()
    for term in forbidden_terms:
        if term in lowered:
            msg = f"Teacher prompt contains forbidden term: {term}"
            raise RuntimeError(msg)
    prompt_ngrams = _ngram_set(revised, 8)
    for example in batch_examples:
        scenario_ngrams = _ngram_set(example.scenario, 8)
        if prompt_ngrams & scenario_ngrams:
            msg = "Teacher prompt copied an 8-token n-gram from a dataset scenario."
            raise RuntimeError(msg)


class GeminiTeacher:
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.cache_dir = config.resolved_teacher_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.template = _load_teacher_template(config.project_root)
        self.client = genai.Client(
            api_key=config.api_key(),
            http_options=types.HttpOptions(timeout=config.teacher.timeout_seconds * 1000),
        )

    def _cache_path(self, payload: dict[str, Any]) -> Path:
        cache_key = sha256_json(
            {
                "model": self.config.teacher.model,
                "temperature": self.config.teacher.temperature,
                "seed": self.config.experiment.seed,
                "payload": payload,
            }
        )
        return self.cache_dir / f"{cache_key}.json"

    def revise_prompt(self, payload: dict[str, Any]) -> tuple[TeacherRevisionResponse, Path]:
        cache_path = self._cache_path(payload)
        if cache_path.exists():
            cached = read_json(cache_path)
            response = _coerce_teacher_response(cached["response"])
            validate_teacher_response(
                response,
                batch_examples=[TeacherBatchExample(**row) for row in payload["batch_examples"]],
                max_chars=int(payload["max_prompt_chars"]),
            )
            return response, cache_path

        response = self._request_revision(payload)
        validate_teacher_response(
            response,
            batch_examples=[TeacherBatchExample(**row) for row in payload["batch_examples"]],
            max_chars=int(payload["max_prompt_chars"]),
        )
        write_json(
            cache_path,
            {
                "request": payload,
                "response": response.model_dump(mode="json"),
            },
        )
        return response, cache_path

    def _request_message(self, payload: dict[str, Any], feedback_hint: str | None) -> str:
        sections = [
            self.template,
            "",
            "Return JSON with exactly these keys: diagnosis_summary, failure_modes, "
            "change_summary, revised_prompt.",
        ]
        if feedback_hint:
            sections.extend(
                ["", "Previous draft failed validation. Fix this issue:", feedback_hint]
            )
        sections.extend(
            [
                "",
                f"Payload:\n{json.dumps(payload, indent=2, ensure_ascii=False)}",
            ]
        )
        return "\n".join(sections)

    def _request_revision(self, payload: dict[str, Any]) -> TeacherRevisionResponse:
        batch_examples = [TeacherBatchExample(**row) for row in payload["batch_examples"]]
        feedback_hint: str | None = None
        last_error: Exception | None = None
        for attempt_index in range(1, self.config.teacher.max_retries + 1):
            message = self._request_message(payload, feedback_hint)
            try:
                response = self.client.models.generate_content(
                    model=self.config.teacher.model,
                    contents=message,
                    config=types.GenerateContentConfig(
                        temperature=self.config.teacher.temperature,
                        top_p=1.0,
                        top_k=1,
                        candidate_count=1,
                        seed=self.config.experiment.seed,
                        response_mime_type="application/json",
                    ),
                )
            except Exception as exc:  # pragma: no cover
                last_error = RuntimeError(
                    f"Gemini request failed for model {self.config.teacher.model}: {exc}"
                )
            else:
                raw_text = response.text or ""
                try:
                    if not raw_text.strip():
                        msg = "Gemini returned an empty response."
                        raise RuntimeError(msg)
                    parsed = _extract_json_payload(raw_text)
                    revision = _coerce_teacher_response(parsed)
                    validate_teacher_response(
                        revision,
                        batch_examples=batch_examples,
                        max_chars=int(payload["max_prompt_chars"]),
                    )
                    return revision
                except (RuntimeError, ValueError, json.JSONDecodeError, ValidationError) as exc:
                    last_error = exc
            if attempt_index == self.config.teacher.max_retries:
                break
            feedback_hint = (
                f"{last_error}. Return a shorter, more general prompt that still stays under "
                f"{int(payload['max_prompt_chars'])} characters and keep the JSON schema exact."
            )
            time.sleep(min(16, 2 ** (attempt_index - 1)))
        if last_error is not None:
            raise last_error
        msg = "Teacher retry loop exited without producing a revision."
        raise RuntimeError(msg)
