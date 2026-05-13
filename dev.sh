#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
}
trap cleanup EXIT INT TERM

# Free ports if already in use
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

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
