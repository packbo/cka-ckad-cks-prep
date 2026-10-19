"""Validate a scenario by running assertions against the live cluster."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
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
    command: str = ""
    expected: str = ""
    got: str = ""


def _describe_command(assertion: dict) -> str:
    """Human-friendly summary of what the assertion checks."""
    if "run" in assertion:
        cmd = assertion["run"]
        # extract the resource and field from common kubectl jsonpath patterns
        import re
        # kubectl get <res> <name> -n <ns> -o jsonpath='{.field.path}'
        m = re.search(
            r"kubectl\s+get\s+(\S+)\s+(\S+)\s+(?:-n\s+(\S+)\s+)?"
            r"-o\s+jsonpath='?\{(\.[^'}]+)\}'?", cmd
        )
        if m:
            res, name, ns, path = m.groups()
            where = f" in ns `{ns}`" if ns else ""
            return f"`{path}` on {res}/{name}{where}"
        # fallback: first 60 chars
        return cmd[:60]
    if "file" in assertion:
        return f"file {assertion['file']}"
    return "?"


def _diagnose_empty(expected: str, assertion: dict) -> str:
    """Hint when the value is empty — the most common exam mistake."""
    cmd = assertion.get("run", "")
    hints = []
    if "NotFound" in cmd or "not found" in cmd:
        hints.append("resource doesn't exist — check name and namespace")
    if ".spec.template" in cmd:
        hints.append("this field is on the POD TEMPLATE (.spec.template), not on .spec directly")
    if "serviceName" in cmd:
        hints.append("serviceName links the StatefulSet to its headless Service — set it in .spec.serviceName")
    if "clusterIP" in cmd and "None" in str(assertion.get("equals", "")):
        hints.append("headless Service: set spec.clusterIP: None explicitly")
    if "availableReplicas" in cmd:
        hints.append("replicas not ready yet — check kubectl get pods for Pending/CrashLoop")
    if "endpoints" in cmd or "addresses" in cmd:
        hints.append("no endpoints — check Service selector matches Pod labels")
    if "nodeSelector" in cmd or "affinity" in cmd:
        hints.append("scheduling constraint — check the node has the required label")
    if "revision" in cmd:
        hints.append("revision counter — do the update then the rollback (undo)")
    if "succeeded" in cmd:
        hints.append("Job hasn't completed — check kubectl get jobs,pods")
    if not hints:
        hints.append("field is empty or not set — inspect with: kubectl get <resource> -o yaml | grep -A5 <field>")
    return hints[0]


def evaluate(assertion: dict) -> AssertionResult:
    """Evaluate one assertion."""
    result = None
    for _ in range(SETTLE_ATTEMPTS):
        result = _evaluate_once(assertion)
        if result.passed or "file" in assertion:
            return result
        time.sleep(SETTLE_SLEEP)
    return result


def _evaluate_once(assertion: dict) -> AssertionResult:
    from cka_sim import env as _env

    cmd_desc = _describe_command(assertion)

    if "run" in assertion:
        cp = run_shell(_env.substitute(assertion["run"]))
        value = (cp.stdout or "").strip()
        if cp.returncode != 0:
            err = cp.stderr.strip()[:120]
            return AssertionResult(
                False,
                f"❌ {cmd_desc}\n   command: {assertion['run'][:80]}\n   error: {err}",
                command=assertion["run"],
                expected=str(assertion.get("equals", assertion.get("contains", ""))),
                got="(command failed)",
            )
    elif "file" in assertion:
        try:
            with open(assertion["file"]) as fh:
                value = fh.read().strip()
        except FileNotFoundError:
            return AssertionResult(
                False,
                f"❌ file not found: {assertion['file']}",
                command=f"cat {assertion['file']}",
                expected=str(assertion.get("equals", assertion.get("contains", ""))),
                got="(missing)",
            )
    else:
        return AssertionResult(False, "assertion has no 'run' or 'file' key")

    if "equals" in assertion:
        expected = str(assertion["equals"]).strip()
        ok = value == expected
        if ok:
            return AssertionResult(True, f"✅ {cmd_desc} == '{expected}'", assertion["run"], expected, value)
        if not value:
            hint = _diagnose_empty(expected, assertion)
            return AssertionResult(
                False,
                f"❌ {cmd_desc}\n   expected: '{expected}'\n   got: (empty)\n   💡 {hint}",
                assertion["run"], expected, value,
            )
        return AssertionResult(
            False,
            f"❌ {cmd_desc}\n   expected: '{expected}'\n   got: '{value}'",
            assertion["run"], expected, value,
        )
    if "contains" in assertion:
        needle = str(assertion["contains"])
        ok = needle in value
        if ok:
            return AssertionResult(True, f"✅ {cmd_desc} contains '{needle}'", assertion["run"], needle, value)
        return AssertionResult(
            False,
            f"❌ {cmd_desc}\n   expected to contain: '{needle}'\n   got: '{value[:80]}'",
            assertion["run"], needle, value,
        )
    return AssertionResult(True, f"✅ {cmd_desc} (ran OK)", assertion["run"], "", value)


def run_all(assertions: List[dict]):
    return [evaluate(a) for a in assertions]
