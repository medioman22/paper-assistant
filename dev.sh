#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
}
trap cleanup EXIT INT TERM

echo "Starting backend…"
cd "$ROOT/backend"
source .venv/bin/activate
python run.py &
BACKEND_PID=$!

echo "Starting frontend…"
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

wait "$BACKEND_PID" "$FRONTEND_PID"
