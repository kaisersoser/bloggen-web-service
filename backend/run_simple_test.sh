#!/bin/bash

echo "🧪 Simple Redis-SSE Bridge Test"
echo "================================"
echo ""

# Check Redis
echo "Checking Redis..."
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is running"
else
    echo "❌ Redis not running - start with: redis-server"
    exit 1
fi

# Check Backend
echo "Checking Backend..."
if curl -k -s https://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ Backend is running"
else
    echo "❌ Backend not running - start with: cd backend && python src/main.py"
    exit 1
fi

echo ""
echo "🚀 Running Automated Test..."
echo ""

# Activate venv and run test
source .venv/bin/activate
python test_automated_e2e.py

echo ""
echo "✅ Test completed! Check output above for results."