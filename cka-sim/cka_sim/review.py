"""Scénarios marqués « à revoir » (:tag) — persistés dans ~/.cache/cka-sim/review.json."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

REVIEW_FILE = os.path.expanduser("~/.cache/cka-sim/review.json")


def _load() -> Dict[str, dict]:
    try:
        with open(REVIEW_FILE) as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data: Dict[str, dict]) -> None:
    os.makedirs(os.path.dirname(REVIEW_FILE), exist_ok=True)
    with open(REVIEW_FILE, "w") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def tag(sid: str, note: Optional[str] = None) -> None:
    data = _load()
    entry = data.get(sid) or {}
    entry["tagged_at"] = datetime.now().isoformat(timespec="seconds")
    if note:
        entry["note"] = note
    data[sid] = entry
    _save(data)


def untag(sid: str) -> None:
    data = _load()
    if sid in data:
        del data[sid]
        _save(data)


def is_tagged(sid: str) -> bool:
    return sid in _load()


def tagged() -> List[Tuple[str, dict]]:
    """Tagged scenarios, oldest tag first (revision queue order)."""
    return sorted(_load().items(), key=lambda kv: kv[1].get("tagged_at", ""))
