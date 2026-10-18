""":cheat [topic] — speed cheatsheet (setup once, jq, jsonpath, kubectl)."""
from __future__ import annotations

import json
from typing import Optional

from cka_sim import ui
from cka_sim.paths import CHEATSHEET_PATH

_cache: Optional[dict] = None


def _load() -> dict:
    global _cache
    if _cache is None:
        try:
            with open(CHEATSHEET_PATH) as fh:
                _cache = json.load(fh)
        except (OSError, ValueError):
            _cache = {}
    return _cache


def topics() -> list[str]:
    return [k for k in _load() if k != "setup_once"]


def _print_entry(e: dict) -> None:
    ui.out(f"  {e['need']}")
    ui.out(f"    → {e['how']}")
    if e.get("note"):
        ui.info(f"      · {e['note']}")


def _print_section(name: str, entries: list) -> None:
    ui.section(f"CHEAT · {name}")
    for e in entries:
        if isinstance(e, str):
            ui.out(f"  {e}")
        else:
            _print_entry(e)


def show(topic: Optional[str] = None) -> None:
    data = _load()
    if not data:
        ui.warn("cheatsheet unavailable (data/cheatsheet.json)")
        return

    if not topic:
        ui.section("CHEAT · vitesse")
        _print_section("setup_once", data.get("setup_once", []))
        ui.out("")
        ui.info("topics → " + "  ".join(f":cheat {t}" for t in topics())
                + "  (ou :cheat <mot-clé> cherche partout)")
        return

    t = topic.lower().strip()
    for key in data:                       # 1) section match
        if t in key.lower():
            _print_section(key, data[key])
            return
    hits = []                              # 2) keyword search everywhere
    for key, entries in data.items():
        for e in entries:
            if isinstance(e, dict) and t in f"{e.get('need','')} {e.get('how','')}".lower():
                hits.append((key, e))
    if hits:
        ui.section(f"CHEAT · recherche « {topic} »")
        for key, e in hits[:8]:
            ui.info(f"[{key}]")
            _print_entry(e)
    else:
        ui.warn(f"rien pour « {topic} » — sections : {', '.join(data.keys())}")
