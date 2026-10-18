"""Scenario engine: load, setup, run interactive loop, score."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

import yaml

from cka_sim import cheatsheet, completion, ui
from cka_sim.cluster import ClusterBackend, run_shell
from cka_sim.hints import PENALTY, show_hint
from cka_sim.paths import SCENARIOS_DIR
from cka_sim.timer import Timer
from cka_sim.validator import run_all


@dataclass
class Scenario:
    id: str
    title: str
    domain: str
    weight: int
    difficulty: str
    question: str
    hints: list = field(default_factory=list)
    setup_apply: Optional[str] = None
    time_estimate: int = 180
    path: str = ""

    @property
    def setup_fullpath(self) -> Optional[str]:
        if not self.setup_apply:
            return None
        if os.path.isabs(self.setup_apply):
            return self.setup_apply
        return os.path.join(os.path.dirname(self.path), self.setup_apply)


@dataclass
class ScenarioResult:
    scenario: Scenario
    passed: bool
    score: float
    hints_used: int
    skipped: bool = False


def load_scenarios() -> List[Scenario]:
    scenarios: List[Scenario] = []
    for root, _, files in os.walk(SCENARIOS_DIR):
        for f in files:
            if f == "scenario.yaml":
                scenarios.append(_load(os.path.join(root, f)))
    scenarios.sort(key=lambda s: s.id)
    return scenarios


def _load(path: str) -> Scenario:
    with open(path) as fh:
        data = yaml.safe_load(fh)
    setup = data.get("setup") or {}
    return Scenario(
        id=data["id"],
        title=data.get("title", data["id"]),
        domain=data.get("domain", "misc"),
        weight=int(data.get("weight", 2)),
        difficulty=data.get("difficulty", "easy"),
        question=data.get("question", "").strip(),
        hints=data.get("hints", []) or [],
        setup_apply=setup.get("apply"),
        time_estimate=int(data.get("time_estimate", 180)),
        path=path,
    )


def _score_of(scenario: Scenario, hints_used: int) -> float:
    pen = PENALTY.get(hints_used, 0.0) if hints_used else 0.0
    return round(max(0.0, scenario.weight * (1.0 - pen)), 2)


def _setup(scenario: Scenario, backend: ClusterBackend) -> None:
    sp = scenario.setup_fullpath
    if sp and os.path.exists(sp):
        ui.info(f"[setup] resetting + applying {os.path.basename(sp)} ...")
        # Delete first: kubectl apply alone NEVER reverts out-of-band patches
        # (kubectl patch/edit/set image don't update last-applied-configuration),
        # so a previously "solved" bug would survive and break the scenario
        # premise on re-runs of the persistent kind cluster.
        run_shell(
            f"kubectl delete -f {sp} --ignore-not-found --wait=true --timeout=30s",
            timeout=60,
        )
        _wait_namespaces_gone(sp)
        backend.apply_file(sp)


def _wait_namespaces_gone(setup_path: str, timeout_s: int = 30) -> None:
    """Block until every namespace declared in setup.yaml is fully gone."""
    import time

    import yaml as _yaml

    try:
        with open(setup_path) as fh:
            docs = [d for d in _yaml.safe_load_all(fh) if d]
    except (OSError, _yaml.YAMLError):
        return
    namespaces = [
        d["metadata"]["name"]
        for d in docs
        if d.get("kind") == "Namespace" and d.get("metadata", {}).get("name")
    ]
    deadline = time.monotonic() + timeout_s
    pending = list(namespaces)
    while pending and time.monotonic() < deadline:
        still = []
        for ns in pending:
            cp = run_shell(
                f"kubectl get ns {ns} --no-headers -o name 2>/dev/null", timeout=10
            )
            if cp.stdout.strip():
                still.append(ns)
        pending = still
        if pending:
            time.sleep(1)
    if pending:
        ui.warn(f"[setup] namespace(s) still terminating: {', '.join(pending)}")


def run_scenario(scenario: Scenario, backend: ClusterBackend, exam_timer: Optional[Timer] = None) -> ScenarioResult:
    ui.section(f"[{scenario.id}] {scenario.title}  ({scenario.domain}, {scenario.weight}%)")
    ui.info(f"difficulty: {scenario.difficulty}  |  suggested: {scenario.time_estimate}s")
    if exam_timer:
        ui.info(f"exam elapsed: {exam_timer.fmt()}")

    _setup(scenario, backend)
    ui.question(scenario.question)
    ui.info("meta-commands:  :hint <1-4>   :check   :cheat [jq|jsonpath|...]   :solution   :skip")
    print()

    hints_used = 0
    completion.setup()
    while True:
        try:
            raw = input(ui.prompt()).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return ScenarioResult(scenario, False, 0.0, hints_used, skipped=True)
        if not raw:
            continue

        if raw.startswith(":"):
            parts = raw.split()
            cmd = parts[0]
            if cmd == ":hint":
                level = int(parts[1]) if len(parts) > 1 else 1
                show_hint(scenario, level, ui)
                hints_used = max(hints_used, level)
            elif cmd == ":check":
                results = run_all(_check_assertions(scenario))
                passed = all(r.passed for r in results) if results else False
                for i, r in enumerate(results, 1):
                    (ui.ok if r.passed else ui.fail)(f"[{i}/{len(results)}] {r.detail}")
                if passed:
                    score = _score_of(scenario, hints_used)
                    ui.banner(f"SOLVED  |  score: {score}/{scenario.weight}  (hints lvl {hints_used})")
                    return ScenarioResult(scenario, True, score, hints_used)
                else:
                    ui.warn("not all checks passed yet — keep going")
            elif cmd == ":cheat" or cmd == ":cheatsheet":
                cheatsheet.show(parts[1] if len(parts) > 1 else None)
            elif cmd == ":solution":
                show_hint(scenario, 4, ui)
                return ScenarioResult(scenario, False, 0.0, 4)
            elif cmd in (":skip", ":next", ":quit"):
                return ScenarioResult(scenario, False, 0.0, hints_used, skipped=True)
            else:
                ui.warn(f"unknown meta-command: {cmd}")
            continue

        expanded = completion.expand_command(raw)
        if expanded != raw:
            ui.info(f"→ {expanded}")
        cp = run_shell(expanded)
        if cp.stdout:
            ui.out(cp.stdout.rstrip())
        if cp.stderr:
            ui.out(cp.stderr.rstrip())
        if cp.returncode != 0 and not cp.stdout and not cp.stderr:
            ui.warn(f"(exit {cp.returncode})")


def _check_assertions(scenario: Scenario) -> list:
    with open(scenario.path) as fh:
        data = yaml.safe_load(fh)
    check = data.get("check") or {}
    return check.get("assertions") or []
