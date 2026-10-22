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
command -v curl   >/dev/null 2>&1 || { apt-get update -qq && as_root apt-get install -y -qq curl; } || true
echo "kubectl: $(kubectl version --client 2>/dev/null | head -1 | awk '{print $3}')"

# --- GitHub CLI (best effort — used to clone/PR from private repos) ---------
#install_gh
function install_gh() {
if ! command -v gh >/dev/null 2>&1; then
  echo "installing GitHub CLI (gh) ..."
  (
    as_root mkdir -p /etc/apt/keyrings
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      | as_root tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
    as_root chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture 2>/dev/null || echo amd64) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      | as_root tee /etc/apt/sources.list.d/github-cli.list >/dev/null
    as_root apt-get update -qq && as_root apt-get install -y -qq gh
  ) >/dev/null 2>&1 && echo "gh: $(gh --version 2>/dev/null | head -1)" \
    || echo "gh: install skipped (no apt or no network) — not critical"
else
  echo "gh: $(gh --version 2>/dev/null | head -1)"
fi
}

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
  echo "No cluster detected — fresh VPS/bare-metal path: docker + kind multi-node cluster."
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

# --- metrics-server (needed for kubectl top / HPA) ---------------------------
if ! kubectl -n kube-system get deploy metrics-server >/dev/null 2>&1; then
  echo "Installing metrics-server (v0.7.2, kind-compatible)..."
  kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.7.2/components.yaml >/dev/null 2>&1
  # kind needs: kubelet-insecure-tls + root user (emptyDir cert generation)
  # NOTE: keep this patch JSON on ONE line — multiline -p breaks on kubectl>=1.33
  kubectl -n kube-system patch deploy metrics-server --type=strategic -p '{"spec":{"template":{"spec":{"securityContext":{"runAsUser":0,"runAsNonRoot":false},"containers":[{"name":"metrics-server","args":["--cert-dir=/tmp","--secure-port=10250","--kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname","--kubelet-insecure-tls","--metric-resolution=15s"],"securityContext":{"runAsUser":0,"runAsNonRoot":false,"allowPrivilegeEscalation":false}}]}}}}' \
    || echo "⚠ metrics-server patch failed — kubectl top may not work"
  kubectl -n kube-system rollout status deploy/metrics-server --timeout=180s 2>&1 | tail -1
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

# ═══════════════════════════════════════════════════════════════════════════
# AUTO-LAUNCH the web exam UI in the background, then print how to reach it.
#   - server-like host WITH a preinstalled cluster (Killercoda): local python
#     server on :8080 -> open the "Traffic Port" tab and enter 8080
#   - fresh host (docker/kind): image built + deployed -> NodePort 30999
# ═══════════════════════════════════════════════════════════════════════════
WEB_LOG=/tmp/cka-sim-web.log
WEB_PIDFILE=/tmp/cka-sim-web.pid
MARKER=/tmp/cka-web-access.txt
WEB_PORT="${CKA_SIM_WEB_PORT:-8080}"

http_ok() { curl -sf -o /dev/null --max-time 3 "$1" 2>/dev/null; }

first_node_ip() {
  kubectl get nodes -o jsonpath='{range .items[*]}{.status.addresses[?(@.type=="InternalIP")].address}{"\n"}{end}' 2>/dev/null | head -1
}

nodeport_of_service() {
  kubectl get svc cka-exam -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null
}

is_killercoda_like() {
  # the terminal itself sits on a kubernetes node (kubeadm/Killercoda playgrounds)
  [ -d /etc/kubernetes/manifests ]
}

is_kind_cluster() {
  # same condition as `run.sh web`: kind context -> web deployed in-cluster (NodePort)
  kubectl config current-context 2>/dev/null | grep -q '^kind-' \
    || { command -v kind >/dev/null 2>&1 && kind get clusters 2>/dev/null | grep -q .; }
}

launch_web_bg() {
  if [ -f "$WEB_PIDFILE" ] && kill -0 "$(cat "$WEB_PIDFILE" 2>/dev/null)" 2>/dev/null; then
    echo "(web already running, pid $(cat "$WEB_PIDFILE"))"
    return 0
  fi
  echo "Launching web exam UI in background (log: $WEB_LOG) ..."
  nohup ./run.sh web >>"$WEB_LOG" 2>&1 &
  echo $! > "$WEB_PIDFILE"
}

echo "=== Web exam UI ==="

# Local web server on :8080 — works for preinstalled clusters AND kind:
# the server runs where docker/node-exec live, so cluster-admin scenarios
# (etcd, kubeadm, trivy, apparmor…) are all available.
if http_ok "http://localhost:${WEB_PORT}/api/state"; then
  echo "web UI already listening on :${WEB_PORT}"
else
  launch_web_bg
  echo -n "waiting for the web server on :${WEB_PORT} "
  for _ in $(seq 1 30); do
    http_ok "http://localhost:${WEB_PORT}/api/state" && break
    echo -n "."; sleep 2
  done
  echo ""
fi

if http_ok "http://localhost:${WEB_PORT}/api/state"; then
  if is_killercoda_like; then
    cat <<EOF2 | tee "$MARKER"

───────────────────────────────────────────────────────────────
 🎓  WEB EXAM UI READY — running in the background on :${WEB_PORT}
 ➜  Open the "Traffic Port" tab (top bar, right of "Terminal")
    and enter the port:   ${WEB_PORT}
    The exam page (questions left, real terminal right) opens.
───────────────────────────────────────────────────────────────
EOF2
  else
    PUB_IP="$(curl -4 -sf --max-time 3 ifconfig.me 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')"
    cat <<EOF2 | tee "$MARKER"

───────────────────────────────────────────────────────────────
 🎓  WEB EXAM UI READY — local server on :${WEB_PORT}
 ➜  on this host     :  http://localhost:${WEB_PORT}
 ➜  from your browser:  http://${PUB_IP:-<ip>}:${WEB_PORT}   (open the firewall)
    (in-cluster pod alternative: ./run.sh web --pod → NodePort 30999)
───────────────────────────────────────────────────────────────
EOF2
  fi
else
  echo "⚠ web server did not come up — inspect $WEB_LOG (or run: ./run.sh web)"
fi

echo ""
echo "Next:"
echo "  ./run.sh list                  # scenario bank (cka by default)"
echo "  ./run.sh run create-deploy     # one scenario"
echo "  ./run.sh web                   # (re)start the browser exam UI"
echo "  ./run.sh --cert ckad list      # CKAD bank"
