#!/usr/bin/env bash
# AI examiner setup: Node.js + npm → opencode → init projet (repo + cluster kind).
# Idempotent, sûr à relancer. Ubuntu/Debian (Killercoda, Codespaces, VM locale).
# Usage:  bash ai-setup.sh          (ou: curl -fsSL .../ai-setup.sh | bash)
set -euo pipefail

REPO_URL="${CKA_PREP_REPO:-https://github.com/packbo/cka-ckad-cks-prep.git}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
LOG="${AI_SETUP_LOG:-/tmp/ai-setup.log}"

log() { echo "[ai-setup] $*"; }
if [ "$(id -u)" -eq 0 ]; then S=""; else S="sudo "; fi

# ── 1. Node.js + npm ─────────────────────────────────────────────
if ! command -v npm >/dev/null 2>&1; then
  log "installation Node.js 22 LTS + npm (NodeSource)..."
  if curl -fsSL https://deb.nodesource.com/setup_22.x | ${S}bash - >>"$LOG" 2>&1; then
    ${S}apt-get install -y -qq nodejs >>"$LOG" 2>&1
  else
    log "NodeSource indisponible → fallback apt nodejs npm..."
    ${S}apt-get update -qq && ${S}apt-get install -y -qq nodejs npm >>"$LOG" 2>&1
  fi
fi
log "node $(node -v) — npm $(npm -v)"

# ── 2. opencode ──────────────────────────────────────────────────
if ! command -v opencode >/dev/null 2>&1; then
  log "installation opencode (npm -g opencode-ai)..."
  if ! npm install -g opencode-ai >>"$LOG" 2>&1; then
    log "npm a échoué → installer officiel..."
    curl -fsSL https://opencode.ai/install | bash >>"$LOG" 2>&1
  fi
  # npm global bin pas toujours dans le PATH
  export PATH="$PATH:$(npm config get prefix 2>/dev/null)/bin:/usr/local/bin"
fi
command -v opencode >/dev/null 2>&1 && log "opencode OK → $(command -v opencode)" \
  || { echo "[ai-setup] ERREUR: opencode non installé (voir $LOG)"; exit 1; }

# ── 3. Init projet (repo + cluster kind) ─────────────────────────
# Résolution du repo : env > dossier parent du script > clone standard > bootstrap
REPO_DIR="${CKA_PREP_DIR:-}"
if [ -z "$REPO_DIR" ]; then
  if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/AGENTS.md" ]; then REPO_DIR="$SCRIPT_DIR"
  elif [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/../AGENTS.md" ]; then REPO_DIR="$(dirname "$SCRIPT_DIR")"
  elif [ -d /root/cka-ckad-cks-prep ]; then REPO_DIR="/root/cka-ckad-cks-prep"
  fi
fi

CLUSTER_UP=no
command -v kubectl >/dev/null 2>&1 && [ "$(kubectl get nodes --no-headers 2>/dev/null | wc -l)" -ge 1 ] && CLUSTER_UP=yes

if [ "$CLUSTER_UP" = "yes" ] && [ -n "$REPO_DIR" ] && [ -d "$REPO_DIR/cka-sim" ]; then
  log "repo + cluster déjà prêts ($REPO_DIR) — init sauté"
else
  BOOT=""
  if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/bootstrap.sh" ]; then BOOT="$SCRIPT_DIR/bootstrap.sh"
  elif [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/../killercoda/bootstrap.sh" ]; then BOOT="$SCRIPT_DIR/../killercoda/bootstrap.sh"; fi
  if [ -n "$BOOT" ]; then
    CKA_PREP_DIR="${REPO_DIR:-/root/cka-ckad-cks-prep}" bash "$BOOT"
  else
    CKA_PREP_DIR="${REPO_DIR:-/root/cka-ckad-cks-prep}" \
      curl -fsSL "${REPO_URL%.git}/main/killercoda/bootstrap.sh" | bash
  fi
  REPO_DIR="${REPO_DIR:-/root/cka-ckad-cks-prep}"
fi

# ── 4. Lancement ─────────────────────────────────────────────────
cat <<EOF

════════════════════════════════════════════════════════
  Prêt ! Prochaines étapes :

  1) Authentifier l'IA (une seule fois, interactif) :
       opencode auth login
     (choisir un provider — free tiers : Google AI Studio, GitHub Copilot)

  2) Lancer l'examinateur IA depuis le repo (AGENTS.md = règles examinateur) :
       cd $REPO_DIR
       opencode

  3) S'entraîner sans IA :
       cd $REPO_DIR/cka-sim && ./run.sh list && ./run.sh exam
════════════════════════════════════════════════════════
EOF
