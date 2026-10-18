#!/usr/bin/env bash
# Bootstrap CKA trainer on any fresh Ubuntu VM with Docker (Killercoda, Codespaces…).
# Idempotent: safe to re-run. Cluster creation takes 2-4 min.
set -euo pipefail

REPO_URL="${CKA_PREP_REPO:-https://github.com/packbo/cka-ckad-cks-prep.git}"
REPO_DIR="${CKA_PREP_DIR:-/root/cka-ckad-cks-prep}"
LOG=/var/log/cka-prep-setup.log

log() { echo "[cka-prep] $*"; }

# 1. kubectl
if ! command -v kubectl >/dev/null 2>&1; then
  log "installing kubectl..."
  K8S_VER="$(curl -sfL https://dl.k8s.io/release/stable.txt)"
  curl -sfL "https://dl.k8s.io/release/${K8S_VER}/bin/linux/amd64/kubectl" -o /usr/local/bin/kubectl
  chmod +x /usr/local/bin/kubectl
fi

# 2. tooling deps for cka-sim/install.sh
command -v jq      >/dev/null 2>&1 || (apt-get update -qq && apt-get install -y -qq jq)      || true
command -v pip3    >/dev/null 2>&1 || (apt-get update -qq && apt-get install -y -qq python3-pip) || true

# 3. this repo
if [ -d "$REPO_DIR/.git" ]; then
  log "updating $REPO_DIR..."
  git -C "$REPO_DIR" pull -q --ff-only || true
else
  log "cloning $REPO_URL..."
  git clone -q "$REPO_URL" "$REPO_DIR"
fi

# 4. kind cluster + python deps (logs in $LOG)
# CKA_SIM_INGRESS=1 : ports 80/443 mappés vers le control-plane → page web publique via Ingress
export CKA_SIM_INGRESS="${CKA_SIM_INGRESS:-1}"
log "running cka-sim install (2-4 min) — log: $LOG"
bash "$REPO_DIR/cka-sim/install.sh" >>"$LOG" 2>&1 || {
  echo "[cka-prep] install reported an issue — inspect $LOG"; exit 0; }

log "done. Try: cd $REPO_DIR/cka-sim && ./run.sh list"
