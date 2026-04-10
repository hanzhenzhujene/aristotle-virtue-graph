from __future__ import annotations

from ethics_prompt_rewrite.models import LabelSemantics


def render_task_prompt(
    *,
    wrapper_template: str,
    mutable_prompt: str,
    scenario: str,
    label_semantics: LabelSemantics,
) -> str:
    prompt = wrapper_template.format(
        mutable_prompt=mutable_prompt.strip(),
        scenario=scenario.strip(),
        acceptable_label=label_semantics.acceptable_label,
        unacceptable_label=label_semantics.unacceptable_label,
    )
    return prompt.strip() + "\n"


def prompt_version_id(prompt_text: str) -> str:
    from ethics_prompt_rewrite.utils import sha256_text

    return sha256_text(prompt_text)[:16]
