#!/usr/bin/env bash
set -u

cd "$(dirname "$0")" || exit 2

if [ "$#" -eq 0 ]; then
  echo "Usage: ./run_job_agent.sh <command> [args]" >&2
  echo "Example: ./run_job_agent.sh run --fixtures tests/fixtures/e2e_fixture.json --preferences config/preferences.example.yaml" >&2
  exit 2
fi

mkdir -p logs
PYTHON=".venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

LOG="logs/scheduler.log"
printf '[%s] starting: %s\n' "$(date -Is)" "$*" >> "$LOG"
"$PYTHON" -m job_agent --config config/config.yaml "$@" >> "$LOG" 2>&1
RC=$?
printf '[%s] exit=%s\n' "$(date -Is)" "$RC" >> "$LOG"
exit "$RC"
