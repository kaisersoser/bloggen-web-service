#!/bin/bash

echo "🚀 Quick Start with SSL Fix"
echo "=========================="

# Set environment variables
export NODE_TLS_REJECT_UNAUTHORIZED=0

# Start backend
echo "📋 Starting backend..."
cd backend && source .venv/bin/activate && python src/main.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
echo "📋 Starting frontend..."
cd ../frontend-nextjs/blog-generator-ui && node dev-secure.js &
FRONTEND_PID=$!

echo ""
echo "🎉 Services starting..."
echo "Backend: https://localhost:5000"
echo "Frontend: https://localhost:3001"
echo ""
echo "⚠️  Browser SSL Warning Fix:"
echo "1. Visit https://localhost:3001"
echo "2. Click 'Advanced' → 'Proceed to localhost (unsafe)'"
echo "3. Application will load normally"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
