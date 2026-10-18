#!/usr/bin/env bash
# Convenience wrapper: ./run.sh <command> [args]
# Examples: ./run.sh list | ./run.sh up | ./run.sh run create-deploy | ./run.sh exam
exec python3 -m cka_sim "$@"
