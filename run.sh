#!/usr/bin/env bash
# Root entry point — dispatches to the shared simulator (cka-sim).
# All certifications share the same engine:  --cert cka | ckad | cks
# Examples:  ./run.sh list   |   ./run.sh --cert ckad list   |   ./run.sh web
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/cka-sim/run.sh" "$@"
