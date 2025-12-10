#!/bin/bash

# SecuScan Frontend Startup Script

echo "🔒 Starting SecuScan Frontend..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is not installed"
    echo "Please install Node.js 18+ from https://nodejs.org"
    exit 1
fi

# Check Node version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "⚠️  Warning: Node.js version is < 18. Some features may not work."
fi

# Check if backend is running
echo "🔍 Checking backend connection..."
if curl -s http://127.0.0.1:8080/api/v1/health > /dev/null 2>&1; then
    echo "✅ Backend is running"
else
    echo "⚠️  Warning: Backend is not responding at http://127.0.0.1:8080"
    echo "   Please start the backend first: cd ../backend && python3 -m backend.main"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
fi

echo ""
echo "✨ Starting development server..."
echo "📍 Frontend: http://localhost:3000"
echo "📍 Backend:  http://127.0.0.1:8080"
echo ""
echo "Press Ctrl+C to stop"
echo ""

npm run dev
