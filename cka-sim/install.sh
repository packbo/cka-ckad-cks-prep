#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${CKA_SIM_CLUSTER:-cka-sim}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== CKA Simulator - Setup ==="

SUDO="$(command -v sudo 2>/dev/null || true)"
as_root() { if [ -n "$SUDO" ]; then $SUDO "$@"; else "$@"; fi; }

# ---------------------------------------------------------------- detection
have_cluster() {
  # at least one Ready node on the CURRENT kubectl context (Killercoda, GKE, kind…)
  kubectl get nodes --no-headers 2>/dev/null | awk '/Ready/ {found=1} END {exit !found}'
}

install_kubectl() {
  echo "kubectl not found. Installing latest stable..."
  [ "$(uname -m)" = "x86_64" ] && ARCH=amd64 || ARCH=arm64
  local V; V="$(curl -fsSL https://dl.k8s.io/release/stable.txt)"
  curl -fsSL "https://dl.k8s.io/release/${V}/bin/linux/${ARCH}/kubectl" -o /tmp/kubectl
  chmod +x /tmp/kubectl
  as_root mv /tmp/kubectl /usr/local/bin/kubectl
}

command -v kubectl >/dev/null 2>&1 || install_kubectl
echo "kubectl: $(kubectl version --client 2>/dev/null | head -1 | awk '{print $3}')"

ENV_MODE=""
if have_cluster; then
  N_NODES=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)
  CTX=$(kubectl config current-context 2>/dev/null || echo "?")
  ENV_MODE="existing"
  echo ""
  echo ">>> Existing Kubernetes cluster detected: context '${CTX}' (${N_NODES} nodes)."
  echo ">>> Nothing to install or create (Killercoda / managed cluster path) — kind is NOT used."
  echo ""
else
  ENV_MODE="fresh"
  echo "No cluster detected — fresh VPS/bare-metal path: kind + multi-node cluster."
  command -v docker >/dev/null 2>&1 || {
    echo "ERROR: docker is required to run kind. Install it first:"
    echo "  curl -fsSL https://get.docker.com | sh"
    exit 1
  }
  if ! command -v kind >/dev/null 2>&1; then
    echo "kind not found. Installing kind v0.20.0..."
    [ "$(uname -m)" = "x86_64" ] && ARCH=amd64 || ARCH=arm64
    curl -fsSL -o ./kind "https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-${ARCH}"
    chmod +x ./kind
    as_root mv ./kind /usr/local/bin/kind
  fi
  echo "kind version: $(kind version)"

  if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    echo "kind cluster '${CLUSTER_NAME}' already exists."
  else
    echo "Creating multi-node cluster '${CLUSTER_NAME}' (1 control-plane + 2 workers)..."
    cat <<EOF | kind create cluster --name "${CLUSTER_NAME}" --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
- role: worker
- role: worker
EOF
  fi
  echo "Waiting for nodes to be Ready..."
  kubectl wait --for=condition=Ready nodes --all --timeout=180s
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq not found. Installing jq (needed for paths(scalars) exercises)..."
  as_root apt-get update -qq && as_root apt-get install -y -qq jq || echo "(install jq manually if assertions using jq fail)"
fi

# --- python deps: venv only when needed -------------------------------------
# Killercoda & co already provide a ready python env: no venv there.
# VPS/desktop with PEP 668 (externally-managed) python: venv required.
# Override:  bash install.sh --venv | --no-venv   (or env CKA_SIM_VENV=force|never|auto)
VENV_MODE="${CKA_SIM_VENV:-auto}"
for a in "$@"; do
  case "$a" in
    --venv)   VENV_MODE=force ;;
    --no-venv) VENV_MODE=never ;;
  esac
done

EXT_MANAGED=0
if python3 -c "import sysconfig,os; raise SystemExit(0 if os.path.exists(os.path.join(sysconfig.get_path('stdlib'),'EXTERNALLY-MANAGED')) else 1)"; then
  EXT_MANAGED=1
fi

USE_VENV=0
case "$VENV_MODE" in
  force) USE_VENV=1 ;;
  never) USE_VENV=0 ;;
  auto)  [ "$EXT_MANAGED" = "1" ] && USE_VENV=1 ;;
esac

echo "Installing python deps... (venv: $VENV_MODE$( [ "$EXT_MANAGED" = 1 ] && echo ", externally-managed python" || echo ", standard python" ))"
if [ "$USE_VENV" = "1" ]; then
  if python3 -m venv "$SCRIPT_DIR/.venv" 2>/dev/null; then
    "$SCRIPT_DIR/.venv/bin/pip" install -q --upgrade pip >/dev/null 2>&1 || true
    "$SCRIPT_DIR/.venv/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
    echo "python deps installed in .venv (run.sh will use it automatically)"
  else
    # venv module unavailable (python3-full missing) -> fall back to system pip
    pip3 install -q -r "$SCRIPT_DIR/requirements.txt" || \
      pip3 install -q --break-system-packages -r "$SCRIPT_DIR/requirements.txt"
  fi
else
  pip3 install -q -r "$SCRIPT_DIR/requirements.txt" || \
    pip3 install -q --break-system-packages -r "$SCRIPT_DIR/requirements.txt"
  echo "installed system-wide (Killercoda-ready). Force a venv with: bash install.sh --venv"
fi

echo ""
echo "=== Setup complete (${ENV_MODE} environment) ==="
kubectl get nodes
echo ""
echo "Next:"
echo "  ./run.sh list                  # scenario bank (cka by default)"
echo "  ./run.sh run create-deploy     # one scenario"
echo "  ./run.sh web                   # browser exam UI (NodePort 30999)"
echo "  ./run.sh --cert ckad list      # once CKAD scenarios are added"
