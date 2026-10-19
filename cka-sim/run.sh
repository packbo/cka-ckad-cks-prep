#!/usr/bin/env bash
# Convenience wrapper: ./run.sh <command> [args]
# Uses the .venv created by install.sh when present, else system python3.
# Self-healing: if python deps are missing, installs them (PEP 668 fallbacks).
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ -x "$DIR/.venv/bin/python3" ]; then
  exec "$DIR/.venv/bin/python3" -m cka_sim "$@"
fi

# system python: ensure the minimal deps (pyyaml, rich) are importable
if ! python3 -c "import yaml" >/dev/null 2>&1; then
  echo "[cka-sim] python deps missing — installing from requirements.txt ..."
  pip3 install -q -r "$DIR/requirements.txt" 2>/dev/null || \
    pip3 install -q --break-system-packages -r "$DIR/requirements.txt" 2>/dev/null || \
    pip3 install -q --user --break-system-packages -r "$DIR/requirements.txt" || {
      echo "ERROR: could not install python deps automatically."
      echo "Run:  bash install.sh"
      exit 1
    }
fi

exec python3 -m cka_sim "$@"
