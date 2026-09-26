#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " Starting Fresh Local AI Content Studio (Local-First)   "
echo "=========================================================="

if [ ! -d ".venv" ]; then
    echo "[1/4] Creating Python virtual environment with uv..."
    uv venv .venv
fi

echo "[2/4] Syncing Python dependencies..."
.venv/bin/python -m pip install -e .

if [ ! -d "apps/web/node_modules" ]; then
    echo "[3/4] Installing web dependencies..."
    npm --prefix apps/web install
fi

echo "[4/4] Starting API, Worker, and Web Dev Servers..."
echo "API:     http://localhost:8400"
echo "Web:     http://localhost:3000"

.venv/bin/uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8400 --reload &
API_PID=$!

.venv/bin/python worker/worker.py &
WORKER_PID=$!

cleanup() {
    echo "Stopping background processes..."
    kill $API_PID $WORKER_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

npm --prefix apps/web run dev
