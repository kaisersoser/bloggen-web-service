#!/bin/bash

echo "🧪 REAL-WORLD REDIS-SSE BRIDGE VALIDATION"
echo "=========================================="
echo ""
echo "This script helps validate the fix with actual blog generation."
echo "It will monitor Redis messages while you generate a blog through the UI."
echo ""

# Check services
echo "🔍 Checking services..."

if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis not running. Start with: redis-server"
    exit 1
fi
echo "✅ Redis is running"

if ! curl -k -s https://localhost:5000/health > /dev/null 2>&1; then
    echo "❌ Backend not running. Start with: cd backend && python src/main.py"
    exit 1
fi
echo "✅ Backend is running"

if ! curl -k -s https://localhost:3001 > /dev/null 2>&1; then
    echo "❌ Frontend not running. Start with: cd frontend-nextjs/blog-generator-ui && npm run dev"
    exit 1
fi
echo "✅ Frontend is running"

echo ""
echo "🚀 INSTRUCTIONS:"
echo "1. Keep this terminal open to monitor Redis messages"
echo "2. Open browser to: https://localhost:3001"
echo "3. Generate a blog post through the UI"
echo "4. Watch for message flow below"
echo ""
echo "🎯 SUCCESS CRITERIA:"
echo "   ✅ Early messages captured (taskcreated, initializing)"
echo "   ✅ Buffer replay working"
echo "   ✅ SSE connection established before first message"
echo "   ✅ Correlation IDs present"
echo ""

read -p "Press ENTER to start monitoring Redis messages..."
echo ""
echo "📡 Monitoring Redis channels... (Ctrl+C to stop)"
echo "================================================="

# Monitor Redis messages
redis-cli monitor