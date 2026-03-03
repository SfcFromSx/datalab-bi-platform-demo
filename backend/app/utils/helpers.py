"""Utility helpers."""

from __future__ import annotations

import json
from typing import Any


def safe_json_dumps(obj: Any, **kwargs) -> str:
    return json.dumps(obj, default=str, ensure_ascii=False, **kwargs)


def truncate(text: str, max_length: int = 500) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
