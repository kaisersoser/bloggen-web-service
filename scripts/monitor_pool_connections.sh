#!/bin/bash
# Database Pool Connection Monitor
# Tracks pool connections before, during, and after blog generation

LOG_FILE="pool_connection_test_$(date +%Y%m%d_%H%M%S).log"
BACKEND_URL="https://localhost:5000"

echo "=========================================="
echo "  Database Pool Connection Monitor"
echo "  $(date)"
echo "  Log: $LOG_FILE"
echo "=========================================="
echo ""

# Function to get pool stats
get_pool_stats() {
    local label="$1"
    echo "[$label - $(date +%H:%M:%S)]" | tee -a "$LOG_FILE"
    
    POOL_DATA=$(curl -s -k ${BACKEND_URL}/health/database-pool 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo "$POOL_DATA" | jq '.' | tee -a "$LOG_FILE"
        
        # Extract key metrics
        INITIALIZED=$(echo "$POOL_DATA" | jq -r '.stats.initialized')
        CLOSED=$(echo "$POOL_DATA" | jq -r '.stats.closed')
        SIZE=$(echo "$POOL_DATA" | jq -r '.stats.size')
        FREE=$(echo "$POOL_DATA" | jq -r '.stats.free')
        IN_USE=$(echo "$POOL_DATA" | jq -r '.stats.in_use')
        MAX_SIZE=$(echo "$POOL_DATA" | jq -r '.stats.max_size')
        
        echo "  Summary: initialized=$INITIALIZED closed=$CLOSED in_use=$IN_USE free=$FREE size=$SIZE max=$MAX_SIZE" | tee -a "$LOG_FILE"
        
        # Alert if pool is marked as closed
        if [ "$CLOSED" = "true" ]; then
            echo "  🚨 WARNING: Pool is marked as CLOSED!" | tee -a "$LOG_FILE"
        fi
        
        # Alert if no free connections
        if [ "$FREE" = "0" ] && [ "$MAX_SIZE" != "0" ]; then
            echo "  ⚠️  WARNING: No free connections available!" | tee -a "$LOG_FILE"
        fi
    else
        echo "  ❌ Failed to get pool stats" | tee -a "$LOG_FILE"
    fi
    echo "" | tee -a "$LOG_FILE"
}

# Function to check backend errors
check_backend_errors() {
    local label="$1"
    echo "[$label - Backend Errors Check]" | tee -a "$LOG_FILE"
    
    RECENT_ERRORS=$(tail -50 /home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/backend.log | grep -i "error\|failed\|exception\|closed")
    
    if [ -n "$RECENT_ERRORS" ]; then
        echo "  Recent errors/warnings found:" | tee -a "$LOG_FILE"
        echo "$RECENT_ERRORS" | tail -10 | sed 's/^/    /' | tee -a "$LOG_FILE"
    else
        echo "  ✅ No recent errors" | tee -a "$LOG_FILE"
    fi
    echo "" | tee -a "$LOG_FILE"
}

# Start monitoring
echo "🔍 Starting Pool Connection Monitoring..." | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Initial state
get_pool_stats "INITIAL STATE"
check_backend_errors "INITIAL STATE"

echo "=========================================="
echo "📝 Instructions:"
echo "1. This script will monitor in intervals"
echo "2. Generate a blog from the UI now"
echo "3. Script will track connections during generation"
echo "4. After completion, check the final state"
echo ""
echo "Monitoring every 5 seconds..."
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

# Counter for tracking
ITERATION=1

# Monitor continuously
while true; do
    sleep 5
    get_pool_stats "ITERATION $ITERATION"
    
    # Every 3rd iteration, check for errors
    if [ $((ITERATION % 3)) -eq 0 ]; then
        check_backend_errors "ITERATION $ITERATION"
    fi
    
    ITERATION=$((ITERATION + 1))
done
