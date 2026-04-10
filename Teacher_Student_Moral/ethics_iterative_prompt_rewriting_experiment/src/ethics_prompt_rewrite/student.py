from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import mlx.core as mx
import torch
from huggingface_hub import snapshot_download
from mlx_lm import load as mlx_load
from mlx_lm.generate import batch_generate
from mlx_lm.sample_utils import make_sampler
from openai import OpenAI
from transformers import AutoModelForCausalLM, AutoTokenizer

from ethics_prompt_rewrite.config import ExperimentConfig
from ethics_prompt_rewrite.utils import chunked


@dataclass
class StudentPrediction:
    predicted_label: int | None
    is_invalid: bool
    raw_output: str
    score_0: float | None = None
    score_1: float | None = None


def parse_binary_label(text: str) -> int | None:
    cleaned = text.strip()
    if cleaned == "0":
        return 0
    if cleaned == "1":
        return 1
    return None


def _resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _resolve_dtype(device: str, requested: str) -> torch.dtype:
    if requested == "float32":
        return torch.float32
    if requested == "float16":
        return torch.float16
    if device in {"cuda", "mps"}:
        return torch.float16
    return torch.float32


class BaseStudentBackend:
    backend_name = "base"

    def predict_batch(self, prompts: list[str]) -> list[StudentPrediction]:
        raise NotImplementedError

    def predict(self, prompts: list[str]) -> list[StudentPrediction]:
        raise NotImplementedError

    def metadata(self) -> dict[str, Any]:
        raise NotImplementedError


class HFTransformersStudent(BaseStudentBackend):
    backend_name = "hf_transformers"

    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.device = _resolve_device(config.student.device)
        self.dtype = _resolve_dtype(self.device, config.student.dtype)
        model_ref = config.student.hf_model_id_or_path
        self.model_path = self._resolve_model_path(model_ref, config.student.hf_local_only)
        self.tokenizer: Any = AutoTokenizer.from_pretrained(
            self.model_path,
            local_files_only=config.student.hf_local_only,
            trust_remote_code=False,
        )
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        zero_ids = self.tokenizer.encode("0", add_special_tokens=False)
        one_ids = self.tokenizer.encode("1", add_special_tokens=False)
        self.binary_token_ids: tuple[int, int] | None = None
        if len(zero_ids) == 1 and len(one_ids) == 1:
            self.binary_token_ids = (zero_ids[0], one_ids[0])
        self.model = cast(
            Any,
            AutoModelForCausalLM.from_pretrained(
                self.model_path,
                local_files_only=config.student.hf_local_only,
                trust_remote_code=False,
                dtype=self.dtype,
            ),
        )
        self.model.to(self.device)
        self.model.eval()

    def _resolve_model_path(self, model_ref: str, local_only: bool) -> str:
        path = Path(model_ref)
        if path.exists():
            return str(path.resolve())
        return snapshot_download(repo_id=model_ref, local_files_only=local_only)

    def _score_candidate(self, prompts: list[str], candidate: str) -> list[float]:
        prompt_ids = self.tokenizer(
            prompts,
            add_special_tokens=False,
            return_attention_mask=False,
        )["input_ids"]
        if not all(len(token_ids) >= 1 for token_ids in prompt_ids):
            msg = "Candidate scoring requires non-empty prompt text."
            raise RuntimeError(msg)
        prompt_lens = torch.tensor(
            [len(token_ids) for token_ids in prompt_ids],
            device=self.device,
            dtype=torch.long,
        )
        full_texts = [prompt + candidate for prompt in prompts]
        encoded = self.tokenizer(
            full_texts,
            add_special_tokens=False,
            padding=True,
            return_tensors="pt",
        )
        input_ids = encoded["input_ids"].to(self.device)
        attention_mask = encoded["attention_mask"].to(self.device)
        with torch.no_grad():
            logits = self.model(input_ids=input_ids, attention_mask=attention_mask).logits
            log_probs = torch.log_softmax(logits[:, :-1, :], dim=-1)
            target_ids = input_ids[:, 1:]
            token_log_probs = log_probs.gather(2, target_ids.unsqueeze(-1)).squeeze(-1)
            token_positions = torch.arange(1, input_ids.shape[1], device=self.device).unsqueeze(0)
            suffix_mask = (token_positions >= prompt_lens.unsqueeze(1)) & (
                attention_mask[:, 1:] == 1
            )
            masked_scores = token_log_probs * suffix_mask
            return [float(score) for score in masked_scores.sum(dim=1).tolist()]

    def predict_batch(self, prompts: list[str]) -> list[StudentPrediction]:
        if self.binary_token_ids is not None:
            return self._predict_batch_single_token(prompts)
        score_0 = self._score_candidate(prompts, "0")
        score_1 = self._score_candidate(prompts, "1")
        results: list[StudentPrediction] = []
        for left, right in zip(score_0, score_1, strict=True):
            predicted_label = 1 if right > left else 0
            results.append(
                StudentPrediction(
                    predicted_label=predicted_label,
                    is_invalid=False,
                    raw_output=str(predicted_label),
                    score_0=left,
                    score_1=right,
                )
            )
        return results

    def _predict_batch_single_token(self, prompts: list[str]) -> list[StudentPrediction]:
        zero_id, one_id = self.binary_token_ids or (None, None)
        if zero_id is None or one_id is None:
            msg = "Single-token binary ids were requested but not available."
            raise RuntimeError(msg)
        encoded = self.tokenizer(
            prompts,
            add_special_tokens=False,
            padding=True,
            return_tensors="pt",
        )
        input_ids = encoded["input_ids"].to(self.device)
        attention_mask = encoded["attention_mask"].to(self.device)
        with torch.no_grad():
            logits = self.model(input_ids=input_ids, attention_mask=attention_mask).logits
            last_positions = attention_mask.sum(dim=1) - 1
            batch_indices = torch.arange(input_ids.shape[0], device=self.device)
            last_logits = logits[batch_indices, last_positions]
            score_0 = last_logits[:, zero_id].tolist()
            score_1 = last_logits[:, one_id].tolist()
        results: list[StudentPrediction] = []
        for left, right in zip(score_0, score_1, strict=True):
            predicted_label = 1 if right > left else 0
            results.append(
                StudentPrediction(
                    predicted_label=predicted_label,
                    is_invalid=False,
                    raw_output=str(predicted_label),
                    score_0=float(left),
                    score_1=float(right),
                )
            )
        return results

    def predict(self, prompts: list[str]) -> list[StudentPrediction]:
        outputs: list[StudentPrediction] = []
        for prompt_chunk in chunked(prompts, self.config.student.batch_size):
            outputs.extend(self.predict_batch(prompt_chunk))
        return outputs

    def metadata(self) -> dict[str, Any]:
        return {
            "backend_name": self.backend_name,
            "model_path": self.model_path,
            "requested_model": self.config.student.hf_model_id_or_path,
            "device": self.device,
            "dtype": str(self.dtype),
        }


class LocalOpenAIStudent(BaseStudentBackend):
    backend_name = "openai_compatible_local"

    def __init__(self, config: ExperimentConfig):
        self.config = config
        base_url = config.student.openai_base_url
        parsed = urlparse(base_url)
        if parsed.hostname not in {"localhost", "127.0.0.1"}:
            msg = "The OpenAI-compatible student backend only allows localhost endpoints."
            raise RuntimeError(msg)
        if not config.student.openai_model:
            msg = "student.openai_model must be set for the OpenAI-compatible backend."
            raise RuntimeError(msg)
        self.client = OpenAI(base_url=base_url, api_key="local")
        self.model_name = config.student.openai_model

    def predict_batch(self, prompts: list[str]) -> list[StudentPrediction]:
        predictions: list[StudentPrediction] = []
        for prompt in prompts:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                top_p=1.0,
                max_tokens=1,
            )
            raw_output = response.choices[0].message.content or ""
            parsed = parse_binary_label(raw_output)
            predictions.append(
                StudentPrediction(
                    predicted_label=parsed,
                    is_invalid=parsed is None,
                    raw_output=raw_output,
                )
            )
        return predictions

    def predict(self, prompts: list[str]) -> list[StudentPrediction]:
        outputs: list[StudentPrediction] = []
        for prompt_chunk in chunked(prompts, self.config.student.batch_size):
            outputs.extend(self.predict_batch(prompt_chunk))
        return outputs

    def metadata(self) -> dict[str, Any]:
        return {
            "backend_name": self.backend_name,
            "base_url": self.config.student.openai_base_url,
            "model": self.config.student.openai_model,
        }


class MLXLMStudent(BaseStudentBackend):
    backend_name = "mlx_lm"

    def __init__(self, config: ExperimentConfig):
        self.config = config
        model_ref = config.student.mlx_model_id_or_path
        if not model_ref:
            msg = "student.mlx_model_id_or_path must be set for the mlx_lm backend."
            raise RuntimeError(msg)
        self.model_ref = model_ref
        self.model, self.tokenizer = cast(tuple[Any, Any], mlx_load(model_ref))
        zero_ids = self.tokenizer.encode("0")
        one_ids = self.tokenizer.encode("1")
        self.binary_token_ids: tuple[int, int] | None = None
        if len(zero_ids) == 1 and len(one_ids) == 1:
            self.binary_token_ids = (zero_ids[0], one_ids[0])

    def _binary_only_logits_processor(self) -> Any:
        zero_id, one_id = self.binary_token_ids or (None, None)
        if zero_id is None or one_id is None:
            return None
        allowed = (zero_id, one_id)

        def restrict(_tokens: Any, logits: Any) -> Any:
            masked = mx.full(logits.shape, -1e9)
            for token_id in allowed:
                masked[:, token_id] = logits[:, token_id]
            return masked

        return restrict

    def predict_batch(self, prompts: list[str]) -> list[StudentPrediction]:
        encoded = [self.tokenizer.encode(prompt) for prompt in prompts]
        kwargs: dict[str, Any] = {}
        processor = self._binary_only_logits_processor()
        if processor is not None:
            kwargs["logits_processors"] = [processor]
        response = batch_generate(
            self.model,
            self.tokenizer,
            encoded,
            max_tokens=1,
            sampler=make_sampler(temp=0.0),
            verbose=False,
            **kwargs,
        )
        results: list[StudentPrediction] = []
        for text in response.texts:
            parsed = parse_binary_label(text)
            results.append(
                StudentPrediction(
                    predicted_label=parsed,
                    is_invalid=parsed is None,
                    raw_output=text,
                )
            )
        return results

    def predict(self, prompts: list[str]) -> list[StudentPrediction]:
        outputs: list[StudentPrediction] = []
        for prompt_chunk in chunked(prompts, self.config.student.batch_size):
            outputs.extend(self.predict_batch(prompt_chunk))
        return outputs

    def metadata(self) -> dict[str, Any]:
        return {
            "backend_name": self.backend_name,
            "model": self.model_ref,
            "requested_model": self.config.student.mlx_model_id_or_path,
        }


def build_student_backend(config: ExperimentConfig) -> BaseStudentBackend:
    if config.student.backend == "hf_transformers":
        return HFTransformersStudent(config)
    if config.student.backend == "mlx_lm":
        return MLXLMStudent(config)
    if config.student.backend == "openai_compatible_local":
        return LocalOpenAIStudent(config)
    msg = f"Unsupported student backend: {config.student.backend}"
    raise RuntimeError(msg)
