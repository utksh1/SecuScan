#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo "⏹  Shutting down..."
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
  [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null
  wait 2>/dev/null
  echo "✓  All processes stopped."
  exit 0
}
trap cleanup INT TERM

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║         SecuScan Dev Server            ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

# Pre-flight checks: kill existing servers on 8000 and 5173
# If ports remain occupied after startup fails, see README.md
# Troubleshooting → Local Startup Troubleshooting.
echo "🧹 Cleaning up existing processes on port 8000 and 5173..."
if command -v lsof &>/dev/null; then
  lsof -ti :8000 | xargs kill -9 2>/dev/null || true
  lsof -ti :5173 | xargs kill -9 2>/dev/null || true
elif command -v netstat &>/dev/null && command -v taskkill &>/dev/null; then
  for port in 8000 5173; do
    pids=$(netstat -ano | grep -i LISTENING | grep -E "[:.]$port[[:space:]]" | awk '{print $5}' | tr -d '\r' | sort -u || true)
    for pid in $pids; do
      if [ -n "$pid" ] && [[ "$pid" =~ ^[0-9]+$ ]]; then
        taskkill //F //PID "$pid" &>/dev/null || true
      fi
    done
  done
fi
sleep 1

# ── Backend ────────────────────────────────────
echo "⚙  Setting up backend..."
cd "$ROOT_DIR"

# Validate project structure before any expensive setup
if [ ! -f "$ROOT_DIR/backend/requirements.txt" ]; then
  echo "ERROR: backend/requirements.txt not found."
  exit 1
fi

if [ ! -d "$ROOT_DIR/frontend" ]; then
  echo "ERROR: frontend directory not found."
  exit 1
fi

# Determine python command (must be Python 3.11+)
PYTHON_CMD=""
if command -v python3 &>/dev/null && python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' &>/dev/null; then
  PYTHON_CMD="python3"
elif command -v python &>/dev/null && python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' &>/dev/null; then
  PYTHON_CMD="python"
else
  echo "ERROR: Python 3.11+ is required to start SecuScan." >&2
  exit 1
fi

if [ ! -d "venv" ]; then
  echo "   Creating virtual environment..."
  $PYTHON_CMD -m venv venv
fi

if [ -d "venv/Scripts" ]; then
  VENV_BIN="venv/Scripts"
else
  VENV_BIN="venv/bin"
fi

source "$VENV_BIN/activate"

pip install -q --upgrade pip
pip install -q -r backend/requirements.txt

mkdir -p "$ROOT_DIR/data" "$ROOT_DIR/logs"

echo "🚀 Starting backend on http://127.0.0.1:8000"
python -m uvicorn backend.secuscan.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload \
  --log-level info &
BACKEND_PID=$!

# ── Frontend ───────────────────────────────────
echo "🚀 Starting frontend on http://127.0.0.1:5173"
cd "$ROOT_DIR/frontend"
# Install dependencies if node_modules missing or broken
if [ ! -d "node_modules" ] || [ ! -f "node_modules/.bin/vite" ]; then
  echo "   Installing/repairing frontend dependencies (npm install)..."
  npm install
fi
npm run dev -- --host 127.0.0.1 --port 5173 &
FRONTEND_PID=$!

cd "$ROOT_DIR"

echo ""
echo "  ┌─────────────────────────────────────────────────────────┐"
echo "  │  Backend  → http://127.0.0.1:8000                       │"
echo "  │  Frontend → http://127.0.0.1:5173                       │"
echo "  │                                                         │"
echo "  │  Documentation:                                         │"
echo "  │  - Swagger UI → http://127.0.0.1:8000/docs              │"
echo "  │  - ReDoc      → http://127.0.0.1:8000/redoc             │"
echo "  │  - OpenAPI    → http://127.0.0.1:8000/openapi.json      │"
echo "  │                                                         │"
echo "  │  Proxy Paths (via Frontend):                            │"
echo "  │  - API Docs   → http://127.0.0.1:5173/api/docs          │"
echo "  └─────────────────────────────────────────────────────────┘"
echo ""
echo "  Press Ctrl+C to stop both servers"
echo ""

wait
