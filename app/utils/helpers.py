from __future__ import annotations

import json
from datetime import datetime
from typing import Any


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def safe_json(value: Any, default: Any = None):
    try:
        return json.loads(value)
    except Exception:
        return default


def to_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        default=str,
    )


def chunk_list(items: list[Any], size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def compact_text(text: str) -> str:
    return " ".join(text.split())


def truncate(text: str, limit: int = 200) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."