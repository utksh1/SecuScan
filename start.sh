#!/bin/bash

echo "🚀 Starting SecuScan Development Server"
echo "========================================="
echo ""

echo "Starting SecuScan servers..."

# Start backend server
echo "Starting backend server..."
source venv_tests/bin/activate
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend server
echo "Starting frontend server..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo "Backend server PID: $BACKEND_PID"
echo "Frontend server PID: $FRONTEND_PID"
echo "Backend running on: http://localhost:8000"
echo "Frontend running on: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
