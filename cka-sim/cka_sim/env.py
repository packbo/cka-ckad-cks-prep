"""Cluster environment detection + scenario adaptation.

Detects the real cluster topology (control-plane, workers, single/multi-node,
docker access, direct node access) and:
  - substitutes %PLACEHOLDER% tokens in questions/hints/solutions/assertions
  - evaluates per-scenario `requires:` (workers, docker, node_exec)
  - reports a non-optimal-environment advisory (best = 1 CP + 2 workers)
"""
from __future__ import annotations

import os
import shutil
import subprocess

_cache = {"data": None}

OPTIMAL_WORKERS = 2


def run(cmd: str) -> str:
    try:
        return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=15).stdout
    except Exception:
        return ""


def detect(force: bool = False) -> dict:
    """Introspect the current cluster. Cached for the process lifetime."""
    if _cache["data"] and not force:
        return _cache["data"]

    out = run("kubectl get nodes -o json 2>/dev/null")
    cp, workers = None, []
    if out:
        import json
        try:
            items = json.loads(out).get("items", [])
        except ValueError:
            items = []
        for it in items:
            name = it["metadata"]["name"]
            labels = it["metadata"].get("labels", {})
            if any(k.startswith("node-role.kubernetes.io/control-plane")
                   or k.startswith("node-role.kubernetes.io/master") for k in labels):
                cp = name
            else:
                workers.append(name)
        if items and cp is None:
            cp = items[0]["metadata"]["name"]  # single-node or unlabeled

    docker = shutil.which("docker") is not None
    exec_style = "none"
    if cp and docker and run(f"docker inspect {cp} >/dev/null 2>&1 && echo ok").strip() == "ok":
        exec_style = "docker"
    elif cp and os.path.isdir("/etc/kubernetes/manifests"):
        exec_style = "direct"  # the terminal itself is a cluster node (kubeadm/Killercoda)

    data = {
        "cp": cp or "",
        "workers": workers,
        "worker": workers[0] if workers else "",
        "worker2": workers[1] if len(workers) > 1 else "",
        "nodes": (1 if cp else 0) + len(workers),
        "docker": docker,
        "exec_style": exec_style,   # docker | direct | none
    }
    _cache["data"] = data
    return data


def placeholders(env: dict = None) -> dict:
    env = env or detect()
    if env["exec_style"] == "docker":
        nodeexec = f"docker exec {env['cp']}"
        cpcp, cpdest = "docker cp", f"{env['cp']}:"
        auditlog = f"docker logs {env['cp']} 2>&1"
    elif env["exec_style"] == "direct":
        nodeexec, cpcp, cpdest = "", "cp", ""
        auditlog = "journalctl -u kube-apiserver --no-pager -n 300 2>/dev/null || cat /var/log/kube-apiserver/audit.log 2>/dev/null"
    else:
        nodeexec, cpcp, cpdest, auditlog = "", "", "", ""
    return {
        "%CP%": env["cp"],
        "%WORKER%": env["worker"],
        "%WORKER2%": env["worker2"],
        "%NODEEXEC%": nodeexec,
        "%CPCP%": cpcp,
        "%CPDEST%": cpdest,
        "%AUDITLOG%": auditlog,
    }


def substitute(text: str, env: dict = None) -> str:
    if not text or "%" not in text:
        return text
    for k, v in placeholders(env).items():
        text = text.replace(k, v)
    return text


def unmet_requires(requires: dict, env: dict = None) -> list:
    """List of human-readable reasons a scenario cannot run here."""
    env = env or detect()
    reasons = []
    if not requires:
        return reasons
    need_workers = int(requires.get("workers", 0))
    if len(env["workers"]) < need_workers:
        reasons.append(f"needs {need_workers} worker node(s), cluster has {len(env['workers'])}")
    if requires.get("docker") and not env["docker"]:
        reasons.append("needs docker on the host")
    if requires.get("node_exec") and env["exec_style"] == "none":
        reasons.append("needs node access (docker exec or a node terminal)")
    return reasons


def advisory(env: dict = None) -> str:
    """Warning shown when the environment is not the optimal topology."""
    env = env or detect()
    w = len(env["workers"])
    if env["nodes"] >= 3 and w >= OPTIMAL_WORKERS:
        return ""
    return (
        f"NON-OPTIMAL ENVIRONMENT: {env['nodes']} node(s) "
        f"({w} worker(s), 1 control-plane). "
        f"Best outcome with 1 control-plane + {OPTIMAL_WORKERS} workers — "
        f"scenarios needing more nodes are auto-skipped."
    )
