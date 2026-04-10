from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class ExperimentSettings(BaseModel):
    name: str
    seed: int
    seeds: list[int]
    bootstrap_samples: int = 2000
    output_root: str = "outputs"


class DataSettings(BaseModel):
    dataset_name: str
    dataset_config: str
    final_test_fraction: float = 0.2
    teacher_dev_fraction_of_development: float = 0.75
    length_bucket_edges: list[int]
    max_examples: int | None = None
    normalize_casefold: bool = True

    @field_validator("final_test_fraction")
    @classmethod
    def validate_final_fraction(cls, value: float) -> float:
        if not 0.0 < value < 1.0:
            msg = "final_test_fraction must be between 0 and 1."
            raise ValueError(msg)
        return value


class StudentSettings(BaseModel):
    backend: str = "hf_transformers"
    hf_model_id_or_path: str
    hf_local_only: bool = True
    mlx_model_id_or_path: str | None = None
    openai_base_url: str = "http://localhost:8000/v1"
    openai_model: str | None = None
    batch_size: int = 16
    device: str = "auto"
    dtype: str = "auto"


class TeacherSettings(BaseModel):
    model: str = "gemini-2.5-pro"
    api_key_env: str = "GEMINI_API_KEY"
    temperature: float = 0.0
    max_prompt_chars: int = 420
    max_retries: int = 5
    timeout_seconds: int = 120


class AdaptationSettings(BaseModel):
    batch_size: int = 32
    max_rounds: int = 12
    min_delta_pp: float = 0.3
    patience: int = 3
    moving_average_window: int = 3


class PromptSettings(BaseModel):
    fixed_prompt: str
    wrapper_template: str


class RuntimeSettings(BaseModel):
    save_teacher_payloads: bool = True
    teacher_cache_dir: str = "outputs/cache/teacher"
    run_notes: str = ""


class ExperimentConfig(BaseModel):
    experiment: ExperimentSettings
    data: DataSettings
    student: StudentSettings
    teacher: TeacherSettings
    adaptation: AdaptationSettings
    prompts: PromptSettings
    runtime: RuntimeSettings
    project_root: Path = Field(default=Path("."))
    config_path: Path | None = None

    def resolved_output_root(self) -> Path:
        return self.project_root / self.experiment.output_root

    def resolved_teacher_cache_dir(self) -> Path:
        return self.project_root / self.runtime.teacher_cache_dir

    def api_key(self) -> str:
        api_key = os.getenv(self.teacher.api_key_env)
        if not api_key:
            msg = f"Missing teacher API key in environment variable {self.teacher.api_key_env}."
            raise RuntimeError(msg)
        return api_key


def load_config(config_path: str | Path) -> ExperimentConfig:
    path = Path(config_path).resolve()
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    config = ExperimentConfig(**raw)
    config.project_root = path.parent.parent
    config.config_path = path
    teacher_model_override = os.getenv("TEACHER_MODEL")
    if teacher_model_override:
        config.teacher.model = teacher_model_override
    return config


def config_to_dict(config: ExperimentConfig) -> dict[str, Any]:
    return config.model_dump(mode="json")
