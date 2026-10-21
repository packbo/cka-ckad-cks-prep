#!/usr/bin/env bash
# Bootstrap CKA trainer on any fresh Ubuntu VM (Killercoda, Codespaces…).
# Idempotent: safe to re-run. Cluster creation takes 2-4 min.
#
# After install, the web exam UI starts AUTOMATICALLY in the background and
# the terminal displays which Traffic Port to open (Killercoda) or which
# NodePort/URL to use (docker/kind hosts).
set -euo pipefail

REPO_URL="${CKA_PREP_REPO:-https://github.com/packbo/cka-ckad-cks-prep.git}"
REPO_DIR="${CKA_PREP_DIR:-/root/cka-ckad-cks-prep}"
LOG=/var/log/cka-prep-setup.log
MARKER=/tmp/cka-web-access.txt

log() { echo "[cka-prep] $*"; }

# 1. kubectl
if ! command -v kubectl >/dev/null 2>&1; then
  log "installing kubectl..."
  K8S_VER="$(curl -sfL https://dl.k8s.io/release/stable.txt)"
  curl -sfL "https://dl.k8s.io/release/${K8S_VER}/bin/linux/amd64/kubectl" -o /usr/local/bin/kubectl
  chmod +x /usr/local/bin/kubectl
fi

# 2. tooling deps for cka-sim/install.sh
command -v curl   >/dev/null 2>&1 || (apt-get update -qq && apt-get install -y -qq curl)       || true
command -v jq     >/dev/null 2>&1 || (apt-get update -qq && apt-get install -y -qq jq)         || true
command -v pip3   >/dev/null 2>&1 || (apt-get update -qq && apt-get install -y -qq python3-pip) || true

# 3. this repo
if [ -d "$REPO_DIR/.git" ]; then
  log "updating $REPO_DIR..."
  git -C "$REPO_DIR" pull -q --ff-only || true
else
  log "cloning $REPO_URL..."
  git clone -q "$REPO_URL" "$REPO_DIR"
fi

# 4. cluster + python deps + AUTO-LAUNCH of the web exam UI
#    (install.sh detects: preinstalled cluster -> local web server on :8080
#     fresh host -> docker + kind -> NodePort 30999)
log "running cka-sim install (2-4 min) — log: $LOG"
bash "$REPO_DIR/cka-sim/install.sh" >>"$LOG" 2>&1 || {
  echo "[cka-prep] install reported an issue — inspect $LOG"; }

# 5. show HOW TO REACH THE WEB UI directly in this terminal
echo ""
if [ -f "$MARKER" ]; then
  cat "$MARKER"
else
  # fallback: derive the message if install could not
  if curl -sf -o /dev/null --max-time 3 http://localhost:8080/api/state 2>/dev/null; then
    cat <<EOF

───────────────────────────────────────────────────────────────
 🎓  WEB EXAM UI READY — running in the background on :8080
 ➜  Open the "Traffic Port" tab (top bar, right of "Terminal")
    and enter the port:   8080
───────────────────────────────────────────────────────────────
EOF
  else
    echo "(web UI not up yet — run:  cd $REPO_DIR/cka-sim && ./run.sh web)"
    echo "  then check $MARKER for the port to open."
  fi
fi

log "done. CLI training also available: cd $REPO_DIR/cka-sim && ./run.sh list"
