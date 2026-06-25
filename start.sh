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
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :5173 | xargs kill -9 2>/dev/null || true
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

if [ -d "venv" ]; then
  source venv/bin/activate
else
  echo "   Creating virtual environment..."
  python3 -m venv venv
  source venv/bin/activate
fi

pip install -q --upgrade pip
pip install -q -r backend/requirements.txt

mkdir -p "$ROOT_DIR/data" "$ROOT_DIR/logs"

echo "🚀 Starting backend on http://127.0.0.1:8000"
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"
BACKEND_LOG="$LOG_DIR/backend.log"
python3 -m uvicorn backend.secuscan.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --log-level info > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
# Brief settle period so uvicorn can parse config and bind cleanly
sleep 2
# Double-check that the port is actually listening; emit a clear message if not
if ! lsof -iTCP:8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "WARNING: uvicorn did not bind to :8000 within ${SETTLE_SECONDS:-2}s start-up delay; showing $BACKEND_LOG tail:"
  tail -n 80 "$BACKEND_LOG" || true
  # Do NOT exit here on start.sh because the smoke-test itself waits separately
fi

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
