#!/bin/bash
# Dual Log Viewer - Shows backend and frontend logs with pool monitoring

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

clear

echo -e "${CYAN}=========================================="
echo "  Dual Log Monitor + Pool Status"
echo "  $(date)"
echo "==========================================${NC}"
echo ""

# Function to get pool status in one line
get_pool_status() {
    POOL_DATA=$(curl -s -k https://localhost:5000/health/database-pool 2>/dev/null)
    if [ $? -eq 0 ]; then
        CLOSED=$(echo "$POOL_DATA" | jq -r '.stats.closed')
        IN_USE=$(echo "$POOL_DATA" | jq -r '.stats.in_use')
        FREE=$(echo "$POOL_DATA" | jq -r '.stats.free')
        SIZE=$(echo "$POOL_DATA" | jq -r '.stats.size')
        MAX=$(echo "$POOL_DATA" | jq -r '.stats.max_size')
        
        if [ "$CLOSED" = "true" ]; then
            echo -e "${RED}🚨 POOL: CLOSED=${CLOSED} in_use=${IN_USE}/${MAX} free=${FREE}${NC}"
        else
            echo -e "${GREEN}✅ POOL: closed=${CLOSED} in_use=${IN_USE}/${MAX} free=${FREE} size=${SIZE}${NC}"
        fi
    else
        echo -e "${RED}❌ Cannot get pool status${NC}"
    fi
}

# Show initial pool status
echo -e "${CYAN}Initial Pool Status:${NC}"
get_pool_status
echo ""

echo -e "${YELLOW}Monitoring logs... (Press Ctrl+C to stop)${NC}"
echo -e "${BLUE}─────────────────────────────────────────${NC}"
echo ""

# Start monitoring with pool status updates
(
    while true; do
        sleep 5
        echo ""
        echo -e "${CYAN}[$(date +%H:%M:%S)] Pool Status Update:${NC}"
        get_pool_status
        echo ""
    done
) &
POOL_MONITOR_PID=$!

# Monitor both logs, highlighting important lines
tail -f backend/backend.log -f frontend-nextjs/blog-generator-ui/frontend.log 2>/dev/null | while IFS= read -r line; do
    if echo "$line" | grep -qi "error\|failed\|exception"; then
        echo -e "${RED}${line}${NC}"
    elif echo "$line" | grep -qi "warning\|warn"; then
        echo -e "${YELLOW}${line}${NC}"
    elif echo "$line" | grep -qi "pool.*closed\|connection not available"; then
        echo -e "${RED}🚨 ${line}${NC}"
    elif echo "$line" | grep -qi "✅\|success\|complete\|initialized"; then
        echo -e "${GREEN}${line}${NC}"
    elif echo "$line" | grep -qi "task.*created\|blog.*generat\|POST.*generate"; then
        echo -e "${CYAN}${line}${NC}"
    else
        echo "$line"
    fi
done

# Cleanup on exit
trap "kill $POOL_MONITOR_PID 2>/dev/null" EXIT
