#!/bin/bash

# Test Runner for Redis-SSE Bridge Fix Validation
# This script helps run the comprehensive end-to-end tests to validate
# all three solutions are working correctly.

echo "🧪 REDIS-SSE BRIDGE FIX - TEST SUITE"
echo "======================================"
echo ""
echo "This test suite validates the three implemented solutions:"
echo "1. ⚡ Immediate SSE Connection (pre-generated task IDs)"
echo "2. 📦 Redis Message Buffering (early message capture)" 
echo "3. 🔄 Synchronous Setup Flow (proper sequencing)"
echo ""

# Check if services are running
echo "🔍 Checking service status..."

# Check Redis
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running. Please start Redis first."
    echo "   Run: redis-server"
    exit 1
fi
echo "✅ Redis is running"

# Check if backend is running
if ! curl -k -s https://localhost:5000/health > /dev/null 2>&1; then
    echo "❌ Backend is not running. Please start the backend first."
    echo "   Run: cd backend && source .venv/bin/activate && python src/main.py"
    exit 1
fi
echo "✅ Backend is running"

# Check if frontend is running  
if ! curl -k -s https://localhost:3001 > /dev/null 2>&1; then
    echo "❌ Frontend is not running. Please start the frontend first."
    echo "   Run: cd frontend-nextjs/blog-generator-ui && npm run dev"
    exit 1
fi
echo "✅ Frontend is running"

echo ""
echo "🚀 All services are running! Choose a test option:"
echo ""
echo "1. 🤖 Automated Test (simulates the complete flow)"
echo "2. 🧑‍💻 Manual Test (guided interactive test with frontend)"
echo "3. 📊 Both Tests (comprehensive validation)"
echo ""

read -p "Enter your choice (1, 2, or 3): " choice

case $choice in
    1)
        echo ""
        echo "🤖 Running Automated Test..."
        echo "=============================="
        cd backend
        python test_automated_e2e.py
        ;;
    2)
        echo ""
        echo "🧑‍💻 Starting Manual Test..."
        echo "============================"
        echo ""
        echo "This test requires manual interaction with the frontend."
        echo "The test will monitor Redis messages while you generate a blog."
        echo ""
        read -p "Press ENTER to start the manual test..."
        cd backend
        python test_e2e_redis_sse_fix.py
        ;;
    3)
        echo ""
        echo "📊 Running Both Tests..."
        echo "======================="
        echo ""
        echo "1/2: Running Automated Test first..."
        cd backend
        python test_automated_e2e.py
        echo ""
        echo "2/2: Starting Manual Test..."
        echo "Please interact with the frontend when prompted."
        read -p "Press ENTER to continue to manual test..."
        python test_e2e_redis_sse_fix.py
        ;;
    *)
        echo "❌ Invalid choice. Please run the script again and choose 1, 2, or 3."
        exit 1
        ;;
esac

echo ""
echo "✅ Test execution completed!"
echo ""
echo "📋 Next Steps:"
echo "- Review the test results above"
echo "- If coverage is 100% and early messages are captured, the fix is successful"
echo "- If issues remain, check the logs for detailed error information"
echo ""
echo "🎯 Expected Success Criteria:"
echo "- ✅ Coverage: 95-100%"
echo "- ✅ Early messages captured (taskcreated, initializing)"  
echo "- ✅ Message buffering active"
echo "- ✅ Buffer replay working"
echo "- ✅ Correlation IDs present"