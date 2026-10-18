"""Progressive hint system.

Levels penalise the score but teach the *research method*, which is the product's
differentiator vs Killer.sh (which has no hints at all).
"""
from __future__ import annotations

# Score penalty applied when a given hint level has been consulted.
PENALTY = {
    1: 0.10,   # orientation
    2: 0.25,   # research method
    3: 0.40,   # doc tip / anti-pitfall
    4: 1.00,   # full solution (0 points)
}

LEVEL_LABEL = {1: "Orientation", 2: "Research method", 3: "Doc tip", 4: "Solution"}


def hints_for(scenario) -> list:
    return scenario.hints or []


def find_level(scenario, level: int):
    for h in hints_for(scenario):
        lvl = h.get("level")
        if lvl == level:
            return h
        if isinstance(lvl, str) and lvl.lower() == "solution" and level == 4:
            return h
    return None


def show_hint(scenario, level: int, ui) -> None:
    h = find_level(scenario, level)
    if not h:
        ui.warn(f"no hint at level {level} for this scenario")
        return
    label = LEVEL_LABEL.get(level, str(level))
    pen = PENALTY.get(level, 0)
    ui.hint(f"[{label}] (-{int(pen*100)}%) {h.get('text','').strip()}")
