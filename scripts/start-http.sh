#!/bin/bash

echo "🚀 Starting Blog Generator in HTTP Mode"
echo "======================================"

# Function to kill background processes on exit
cleanup() {
    echo "🛑 Stopping services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}
trap cleanup INT

# Start backend
echo "📋 Starting backend (HTTP)..."
cd backend
source .venv/bin/activate
python src/main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend  
echo "📋 Starting frontend (HTTP)..."
cd frontend-nextjs/blog-generator-ui
npm run dev:http &
FRONTEND_PID=$!
cd ../..

echo ""
echo "🎉 Services started successfully!"
echo "================================"
echo "🔗 Backend:  http://localhost:5000"
echo "🔗 Frontend: http://localhost:3001"
echo ""
echo "✅ No SSL certificate issues in HTTP mode"
echo "🌐 Visit: http://localhost:3001"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
wait
