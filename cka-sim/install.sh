#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${CKA_SIM_CLUSTER:-cka-sim}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== CKA Simulator - Setup ==="

if ! command -v kubectl >/dev/null 2>&1; then
  echo "ERROR: kubectl is not installed. Install it first:"
  echo "  https://kubernetes.io/docs/tasks/tools/"
  exit 1
fi

if ! command -v kind >/dev/null 2>&1; then
  echo "kind not found. Installing kind v0.20.0..."
  [ "$(uname -m)" = "x86_64" ] && ARCH=amd64 || ARCH=arm64
  curl -Lo ./kind "https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-${ARCH}"
  chmod +x ./kind
  sudo mv ./kind /usr/local/bin/kind
fi
echo "kind version: $(kind version)"

if ! command -v jq >/dev/null 2>&1; then
  echo "jq not found. Installing jq (needed for paths(scalars) exercises)..."
  sudo apt-get update -qq && sudo apt-get install -y -qq jq
fi

echo "Installing python deps..."
pip3 install -q -r requirements.txt || pip install -q -r requirements.txt

if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
  echo "Cluster '${CLUSTER_NAME}' already exists."
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

echo ""
echo "=== Setup complete ==="
kubectl get nodes
echo ""
echo "Verify the CLI works (no cluster needed):"
echo "  ./run.sh list"
echo "  ./run.sh status"
echo ""
echo "Start a scenario once the cluster is up:"
echo "  ./run.sh run create-deploy"
