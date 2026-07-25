"""Loader for the evaluation gold set."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_GOLD_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "eval" / "gold_set.json"


def load_gold_set(path: Path | None = None) -> list[dict[str, Any]]:
    gold_path = path or _GOLD_PATH
    if not gold_path.exists():
        return []
    data = json.loads(gold_path.read_text(encoding="utf-8"))
    return data.get("cases", [])
