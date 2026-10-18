"""Validate a scenario by running assertions against the live cluster."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from cka_sim.cluster import run_shell


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
    """
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
