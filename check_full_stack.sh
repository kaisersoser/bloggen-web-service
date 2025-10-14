#!/bin/bash
# Full Stack Status Check
# Comprehensive health check for both backend and frontend

echo "=========================================="
echo "  Full Stack Status Check"
echo "  $(date)"
echo "=========================================="
echo ""

# Check Backend
echo "🔴 BACKEND STATUS"
echo "------------------------------------------"
cd /home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend

if pgrep -f "python src/main.py" > /dev/null; then
    BACKEND_PID=$(pgrep -f "python src/main.py" | head -1)
    echo "  ✅ Process running (PID: $BACKEND_PID)"
    
    # Check database pool
    POOL_STATUS=$(curl -s -k https://localhost:5000/health/database-pool 2>/dev/null)
    if [ $? -eq 0 ]; then
        DB_CLOSED=$(echo "$POOL_STATUS" | jq -r '.stats.closed' 2>/dev/null)
        DB_IN_USE=$(echo "$POOL_STATUS" | jq -r '.stats.in_use' 2>/dev/null)
        DB_MAX=$(echo "$POOL_STATUS" | jq -r '.stats.max_size' 2>/dev/null)
        
        if [ "$DB_CLOSED" = "false" ]; then
            echo "  ✅ Database pool healthy (closed=$DB_CLOSED)"
            echo "     Connections: $DB_IN_USE / $DB_MAX in use"
        else
            echo "  ❌ Database pool closed!"
        fi
    else
        echo "  ⚠️  Could not check database status"
    fi
    
    # Recent errors
    ERROR_COUNT=$(grep -c "ERROR" backend.log 2>/dev/null || echo "0")
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo "  ⚠️  $ERROR_COUNT error(s) in log"
    else
        echo "  ✅ No errors in log"
    fi
else
    echo "  ❌ Backend NOT running"
fi
echo ""

# Check Frontend
echo "🔵 FRONTEND STATUS"
echo "------------------------------------------"
cd /home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/frontend-nextjs/blog-generator-ui

if pgrep -f "dev-https" > /dev/null 2>&1; then
    FRONTEND_PID=$(pgrep -f "dev-https" | head -1)
    echo "  ✅ Process running (PID: $FRONTEND_PID)"
    
    # Check if responding
    HTTP_CODE=$(curl -s -k -o /dev/null -w "%{http_code}" https://localhost:3001 2>/dev/null)
    if [ "$HTTP_CODE" = "200" ]; then
        RESPONSE_TIME=$(curl -s -k -o /dev/null -w "%{time_total}" https://localhost:3001 2>/dev/null)
        echo "  ✅ Server responding (${RESPONSE_TIME}s)"
    else
        echo "  ⚠️  Server not responding correctly"
    fi
    
    # Recent errors
    if [ -f "frontend.log" ]; then
        FRONTEND_ERRORS=$(tail -100 frontend.log | grep -ci "error" 2>/dev/null || echo "0")
        if [ "$FRONTEND_ERRORS" -gt 5 ]; then
            echo "  ⚠️  $FRONTEND_ERRORS error mention(s) in recent log"
        else
            echo "  ✅ Minimal errors in log"
        fi
    fi
else
    echo "  ❌ Frontend NOT running"
fi
echo ""

# System Resources
echo "🖥️  SYSTEM RESOURCES"
echo "------------------------------------------"
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
MEM_USAGE=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')

echo "  CPU: ${CPU_USAGE}%"
echo "  Memory: ${MEM_USAGE}%"
echo "  Disk: ${DISK_USAGE}%"
echo ""

# Quick Access URLs
echo "🌐 ACCESS URLS"
echo "------------------------------------------"
echo "  Frontend: https://localhost:3001"
echo "  Backend:  https://localhost:5000"
echo "  Monitoring: https://localhost:3001/admin/monitoring"
echo ""

# Log Files
echo "📝 LOG FILES"
echo "------------------------------------------"
echo "  Backend:  backend/backend.log"
echo "  Frontend: frontend-nextjs/blog-generator-ui/frontend.log"
echo ""

# Summary
echo "=========================================="
if pgrep -f "python src/main.py" > /dev/null && pgrep -f "dev-https" > /dev/null 2>&1; then
    echo "  ✅ Full Stack Operational"
else
    echo "  ⚠️  Some Services Down"
fi
echo "=========================================="
