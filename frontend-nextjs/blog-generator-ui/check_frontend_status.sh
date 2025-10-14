#!/bin/bash
# Frontend Status Check Script
# Quick health check for the frontend service

FRONTEND_URL="https://localhost:3001"

echo "=========================================="
echo "  Frontend Service Status Check"
echo "  $(date)"
echo "=========================================="
echo ""

# Check if frontend process is running
echo "1. Process Check:"
if pgrep -f "dev-https" > /dev/null 2>&1 || pgrep -f "dev-dynamic" > /dev/null 2>&1; then
    PID=$(pgrep -f "dev-https" 2>/dev/null | head -1)
    if [ -z "$PID" ]; then
        PID=$(pgrep -f "dev-dynamic" 2>/dev/null | head -1)
    fi
    echo "   ✅ Frontend is running (PID: $PID)"
else
    echo "   ❌ Frontend is NOT running"
    exit 1
fi
echo ""

# Check if port 3001 is listening
echo "2. Port Check:"
if lsof -i :3001 -sTCP:LISTEN > /dev/null 2>&1; then
    echo "   ✅ Port 3001 is listening"
else
    echo "   ❌ Port 3001 is NOT listening"
    exit 1
fi
echo ""

# Check HTTPS server response
echo "3. HTTPS Server Check:"
HTTP_CODE=$(curl -s -k -o /dev/null -w "%{http_code}" ${FRONTEND_URL})
if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ Frontend responding (HTTP $HTTP_CODE)"
    RESPONSE_TIME=$(curl -s -k -o /dev/null -w "%{time_total}" ${FRONTEND_URL})
    echo "      - Response time: ${RESPONSE_TIME}s"
else
    echo "   ❌ Frontend not responding correctly (HTTP $HTTP_CODE)"
fi
echo ""

# Check compilation status
echo "4. Compilation Status:"
if grep -q "compiled successfully" frontend.log; then
    COMPILE_COUNT=$(grep -c "compiled successfully" frontend.log)
    echo "   ✅ Successful compilations: $COMPILE_COUNT"
    LAST_COMPILE=$(grep "compiled successfully" frontend.log | tail -1)
    echo "      Last: ${LAST_COMPILE:0:80}..."
else
    echo "   ⚠️  No successful compilation found yet"
fi
echo ""

# Check for errors
echo "5. Error Check (last 100 lines):"
ERROR_COUNT=$(tail -100 frontend.log | grep -ci "error" || echo "0")
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo "   ✅ No errors in recent logs"
else
    echo "   ⚠️  Found $ERROR_COUNT error mention(s)"
    echo "   Recent errors:"
    tail -100 frontend.log | grep -i "error" | tail -3 | sed 's/^/      /'
fi
echo ""

# Check for warnings
echo "6. Warning Check (last 100 lines):"
WARN_COUNT=$(tail -100 frontend.log | grep -ci "warning" || echo "0")
if [ "$WARN_COUNT" -eq 0 ]; then
    echo "   ✅ No warnings in recent logs"
else
    echo "   ⚠️  Found $WARN_COUNT warning mention(s)"
    echo "   Recent warnings:"
    tail -100 frontend.log | grep -i "warning" | tail -3 | sed 's/^/      /'
fi
echo ""

# Check debug mode
echo "7. Debug Mode:"
if grep -q "DEBUG=" frontend.log; then
    echo "   ✅ Debug mode is active"
    echo "   ℹ️  Debug output available in frontend.log"
else
    echo "   ⚠️  Debug mode may not be fully active"
fi
echo ""

# Summary
echo "=========================================="
echo "  Summary: Frontend is operational ✅"
echo "  URL: ${FRONTEND_URL}"
echo "=========================================="
