#!/usr/bin/env bash
# Convenience wrapper: ./run.sh <command> [args]
# Uses the .venv created by install.sh when present, else system python3.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -x "$DIR/.venv/bin/python3" ]; then
  exec "$DIR/.venv/bin/python3" -m cka_sim "$@"
fi
exec python3 -m cka_sim "$@"
