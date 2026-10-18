"""Cluster backend abstraction.

The engine is written against the abstract ``ClusterBackend`` interface so the
local ``KindBackend`` can later be swapped for a ``VclusterBackend`` (hosted SaaS)
without touching the scenario engine.
"""
from __future__ import annotations

import shutil
import subprocess
from abc import ABC, abstractmethod


def run_shell(cmd: str, timeout: int = 90) -> subprocess.CompletedProcess:
    """Run a shell command string (supports pipes via bash -c)."""
    try:
        return subprocess.run(
            ["bash", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, returncode=124, stdout="", stderr="timeout")


class ClusterBackend(ABC):
    """Abstract interface every backend (kind, vcluster, ...) must implement."""

    name: str = "abstract"

    @abstractmethod
    def create(self) -> None: ...

    @abstractmethod
    def destroy(self) -> None: ...

    @abstractmethod
    def ready(self) -> bool: ...

    @abstractmethod
    def reset(self) -> None: ...

    @abstractmethod
    def apply_file(self, path: str) -> subprocess.CompletedProcess: ...


class KindBackend(ClusterBackend):
    """kind-based local cluster (multi-node)."""

    name = "kind"
    CLUSTER_NAME = "cka-sim"

    def _kind(self, *args: str) -> subprocess.CompletedProcess:
        return run_shell(" ".join(["kind", *args]))

    def exists(self) -> bool:
        cp = self._kind("get", "clusters")
        return self.CLUSTER_NAME in (cp.stdout or "")

    def create(self) -> None:
        if self.exists():
            print(f"[cluster] kind cluster '{self.CLUSTER_NAME}' already exists")
            self._use_context()
            return
        print(f"[cluster] creating kind cluster '{self.CLUSTER_NAME}' (1 cp + 2 workers)...")
        config = """kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
- role: worker
- role: worker
"""
        ps = subprocess.run(
            ["kind", "create", "cluster", "--name", self.CLUSTER_NAME, "--config", "-"],
            input=config,
            text=True,
            capture_output=True,
        )
        print(ps.stdout)
        if ps.returncode != 0:
            print(ps.stderr)
            raise RuntimeError("kind create cluster failed")
        run_shell("kubectl wait --for=condition=Ready nodes --all --timeout=180s")

    def destroy(self) -> None:
        if not self.exists():
            print(f"[cluster] no kind cluster '{self.CLUSTER_NAME}'")
            return
        print(f"[cluster] deleting kind cluster '{self.CLUSTER_NAME}'...")
        self._kind("delete", "cluster", "--name", self.CLUSTER_NAME)

    def _use_context(self) -> None:
        ctx = f"kind-{self.CLUSTER_NAME}"
        run_shell(f"kubectl config use-context {ctx}")

    def ready(self) -> bool:
        cp = run_shell("kubectl get nodes -o name")
        return cp.returncode == 0 and bool(cp.stdout.strip())

    def reset(self) -> None:
        print("[cluster] resetting namespaces state...")
        run_shell("kubectl delete pods,services,deployments,jobs,cronjobs,configmaps,secrets,pvc -A --all --ignore-not-found")

    def apply_file(self, path: str) -> subprocess.CompletedProcess:
        return run_shell(f"kubectl apply -f {path}")


def kind_installed() -> bool:
    return shutil.which("kind") is not None


def kubectl_installed() -> bool:
    return shutil.which("kubectl") is not None
