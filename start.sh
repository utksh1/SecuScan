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
echo "🧹 Cleaning up existing processes on port 8000 and 5173..."
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :5173 | xargs kill -9 2>/dev/null || true
sleep 1

# ── Backend ────────────────────────────────────
echo "⚙  Setting up backend..."
cd "$ROOT_DIR"

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
python3 -m uvicorn backend.secuscan.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload \
  --log-level info &
BACKEND_PID=$!

# ── Frontend ───────────────────────────────────
echo "🚀 Starting frontend on http://127.0.0.1:5173"
cd "$ROOT_DIR/frontend"
# Install dependencies if node_modules missing
if [ ! -d "node_modules" ]; then
  echo "   Installing frontend dependencies..."
  npm install --silent
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
