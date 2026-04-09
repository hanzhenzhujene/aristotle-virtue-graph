from __future__ import annotations

import html
import re

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_paragraph_text(text: str) -> str:
    normalized = html.unescape(text).replace("\xa0", " ")
    return _WHITESPACE_RE.sub(" ", normalized).strip()
