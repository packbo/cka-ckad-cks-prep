"""Score reporter: weighted results + weak-domain breakdown."""
from __future__ import annotations

from collections import defaultdict
from typing import List

from cka_sim import ui
from cka_sim.engine import ScenarioResult


def report(results: List[ScenarioResult], total_possible: float, elapsed: str) -> None:
    ui.section("EXAM REPORT")
    earned = sum(r.score for r in results)
    pct = (earned / total_possible * 100.0) if total_possible else 0.0
    line = f"Score: {earned:.1f} / {total_possible:.1f}  ({pct:.1f}%)"
    if pct >= 66:
        ui.ok(line + "   -> PASS (threshold 66%)")
    else:
        ui.fail(line + "   -> below 66% pass threshold")

    print()
    ui.info(f"Time used: {elapsed}")
    print()
    _by_domain(results)
    _per_question(results)


def _by_domain(results: List[ScenarioResult]) -> None:
    dom = defaultdict(lambda: [0.0, 0.0])
    for r in results:
        dom[r.scenario.domain][0] += r.score
        dom[r.scenario.domain][1] += r.scenario.weight
    ui.info("By domain:")
    print(f"  {'domain':28} {'score':>8} {'max':>6}")
    for name, (got, mx) in sorted(dom.items()):
        flag = "OK " if got >= mx * 0.6 else "!! "
        print(f"  {flag}{name:26} {got:>6.1f} {mx:>6.1f}")


def _per_question(results: List[ScenarioResult]) -> None:
    print()
    ui.info("Per question:")
    for r in results:
        status = "solved" if r.passed else ("skipped" if r.skipped else "failed")
        print(f"  [{r.scenario.id:24}] {status:8} {r.score:>5.1f}/{r.scenario.weight}  hints:{r.hints_used}")
