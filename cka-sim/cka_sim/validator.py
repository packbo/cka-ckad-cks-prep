"""Validate a scenario by running assertions against the live cluster."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List

from cka_sim.cluster import run_shell

# Controllers need a moment to reconcile (endpoints after a selector fix,
# availableReplicas mid-rollout, .status.succeeded on a Job...). Retry failed
# run-assertions briefly before reporting FAIL. File assertions: no retry.
SETTLE_ATTEMPTS = 4
SETTLE_SLEEP = 3


@dataclass
class AssertionResult:
    passed: bool
    detail: str


def evaluate(assertion: dict) -> AssertionResult:
    """Evaluate one assertion.

    An assertion has either:
      - run: <shell command>   (executed; stdout is the value)
      - file: <path>           (file content is the value)
    and one expectation:
      - contains: <substring>
      - equals: <exact value>

    Empty values are retried a few times (controllers need a moment to
    populate status/endpoints); non-empty wrong values fail immediately.
    """
    result = None
    for _ in range(SETTLE_ATTEMPTS):
        result = _evaluate_once(assertion)
        if result.passed or "file" in assertion:
            return result
        time.sleep(SETTLE_SLEEP)
    return result


def _evaluate_once(assertion: dict) -> AssertionResult:
    if "run" in assertion:
        cp = run_shell(assertion["run"])
        value = (cp.stdout or "").strip()
        if cp.returncode != 0:
            return AssertionResult(False, f"command failed: {cp.stderr.strip()[:120]}")
    elif "file" in assertion:
        try:
            with open(assertion["file"]) as fh:
                value = fh.read().strip()
        except FileNotFoundError:
            return AssertionResult(False, f"file not found: {assertion['file']}")
    else:
        return AssertionResult(False, "assertion has no 'run' or 'file' key")

    if "equals" in assertion:
        expected = str(assertion["equals"]).strip()
        ok = value == expected
        return AssertionResult(ok, f"equals '{expected}' | got '{value}'")
    if "contains" in assertion:
        needle = str(assertion["contains"])
        ok = needle in value
        return AssertionResult(ok, f"contains '{needle}' | got '{value[:80]}'")
    return AssertionResult(True, "ok (ran, no expectation)")


def run_all(assertions: List[dict]):
    return [evaluate(a) for a in assertions]
