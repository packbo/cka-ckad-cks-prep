#!/usr/bin/env bash
# Root entry point — full setup (kind + deps + cluster), then see ./run.sh
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$DIR/cka-sim/install.sh" "$@"
