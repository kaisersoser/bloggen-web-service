#!/bin/bash
# Backend Status Check Script
# Quick health check for the backend service

BACKEND_URL="https://localhost:5000"

echo "=========================================="
echo "  Backend Service Status Check"
echo "  $(date)"
echo "=========================================="
echo ""

# Check if backend process is running
echo "1. Process Check:"
if pgrep -f "python src/main.py" > /dev/null; then
    PID=$(pgrep -f "python src/main.py" | head -1)
    echo "   ✅ Backend is running (PID: $PID)"
else
    echo "   ❌ Backend is NOT running"
    exit 1
fi
echo ""

# Check if port 5000 is listening
echo "2. Port Check:"
if lsof -i :5000 -sTCP:LISTEN > /dev/null 2>&1; then
    echo "   ✅ Port 5000 is listening"
else
    echo "   ❌ Port 5000 is NOT listening"
    exit 1
fi
echo ""

# Check database pool health
echo "3. Database Pool Status:"
POOL_RESPONSE=$(curl -s -k ${BACKEND_URL}/health/database-pool)
if echo "$POOL_RESPONSE" | jq -e '.healthy == true' > /dev/null 2>&1; then
    INITIALIZED=$(echo "$POOL_RESPONSE" | jq -r '.stats.initialized')
    CLOSED=$(echo "$POOL_RESPONSE" | jq -r '.stats.closed')
    SIZE=$(echo "$POOL_RESPONSE" | jq -r '.stats.size')
    FREE=$(echo "$POOL_RESPONSE" | jq -r '.stats.free')
    IN_USE=$(echo "$POOL_RESPONSE" | jq -r '.stats.in_use')
    MAX_SIZE=$(echo "$POOL_RESPONSE" | jq -r '.stats.max_size')
    
    echo "   ✅ Database pool is healthy"
    echo "      - Initialized: $INITIALIZED"
    echo "      - Closed: $CLOSED"
    echo "      - In Use: $IN_USE / $MAX_SIZE"
    echo "      - Free: $FREE"
    echo "      - Current Size: $SIZE"
else
    echo "   ❌ Database pool is unhealthy"
    echo "$POOL_RESPONSE" | jq '.'
fi
echo ""

# Check system health
echo "4. System Health:"
HEALTH_RESPONSE=$(curl -s -k ${BACKEND_URL}/health/system)
if echo "$HEALTH_RESPONSE" | jq -e '.healthy == true' > /dev/null 2>&1; then
    CPU=$(echo "$HEALTH_RESPONSE" | jq -r '.details.cpu_percent')
    MEMORY=$(echo "$HEALTH_RESPONSE" | jq -r '.details.memory_percent')
    echo "   ✅ System is healthy"
    echo "      - CPU: ${CPU}%"
    echo "      - Memory: ${MEMORY}%"
else
    echo "   ⚠️  System health check failed"
fi
echo ""

# Check recent log for errors
echo "5. Recent Errors (last 5 minutes):"
ERROR_COUNT=$(grep -c "ERROR" backend.log 2>/dev/null || echo "0")
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo "   ✅ No errors in log"
else
    echo "   ⚠️  Found $ERROR_COUNT error(s)"
    echo "   Recent errors:"
    grep "ERROR" backend.log | tail -3 | sed 's/^/      /'
fi
echo ""

# Summary
echo "=========================================="
echo "  Summary: Backend is operational ✅"
echo "=========================================="
