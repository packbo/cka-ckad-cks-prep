#!/usr/bin/env bash
# Killercoda background script: runs while the intro page is displayed.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Works whether this folder was cloned standalone or as part of the repo
BOOT="$SCRIPT_DIR/bootstrap.sh"
[ -f "$BOOT" ] || BOOT="$(dirname "$SCRIPT_DIR")/bootstrap.sh"
bash "$BOOT"
