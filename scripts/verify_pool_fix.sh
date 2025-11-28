#!/bin/bash
# Database Pool Health Verification Script
# Tests if the pool closure bug is fixed

set -e

echo "🔍 Database Pool Closure Bug - Verification Test"
echo "================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check pool status
check_pool_status() {
    local test_name=$1
    echo -e "${YELLOW}Testing: $test_name${NC}"
    
    response=$(curl -s -k https://localhost:5000/health/database-pool)
    
    if [ -z "$response" ]; then
        echo -e "${RED}❌ FAILED: Backend not responding${NC}"
        exit 1
    fi
    
    is_closed=$(echo "$response" | jq -r '.stats.closed')
    is_initialized=$(echo "$response" | jq -r '.stats.initialized')
    pool_size=$(echo "$response" | jq -r '.stats.size')
    
    echo "  Pool Status:"
    echo "    - Initialized: $is_initialized"
    echo "    - Closed: $is_closed"
    echo "    - Size: $pool_size"
    
    if [ "$is_closed" = "true" ]; then
        echo -e "${RED}❌ FAILED: Pool is CLOSED${NC}"
        echo "$response" | jq .
        return 1
    elif [ "$is_initialized" = "false" ]; then
        echo -e "${RED}❌ FAILED: Pool not initialized${NC}"
        return 1
    else
        echo -e "${GREEN}✅ PASSED: Pool is healthy${NC}"
        return 0
    fi
}

# Test 1: Initial pool status
echo "Test 1: Initial Pool Status"
echo "----------------------------"
if check_pool_status "Initial state"; then
    echo ""
else
    echo -e "${RED}Test 1 FAILED - Exiting${NC}"
    exit 1
fi

# Test 2: After waiting (let workers initialize)
echo "Test 2: Pool Status After 5 Seconds"
echo "------------------------------------"
sleep 5
if check_pool_status "After initialization period"; then
    echo ""
else
    echo -e "${RED}Test 2 FAILED - Exiting${NC}"
    exit 1
fi

# Instructions for manual testing
echo "================================"
echo -e "${YELLOW}Manual Testing Required:${NC}"
echo ""
echo "Please perform the following tests:"
echo ""
echo "1. Generate Blog #1 via frontend or API"
echo "2. Wait for completion"
echo "3. Run this script again to check pool status"
echo "4. Generate Blog #2"
echo "5. Run this script again"
echo ""
echo "Expected Results:"
echo "  - Blog #1: ✅ Success"
echo "  - Pool Status: ✅ closed=false"
echo "  - Blog #2: ✅ Success (THIS WAS FAILING BEFORE)"
echo "  - Pool Status: ✅ closed=false"
echo ""
echo "If ALL blogs succeed and pool stays healthy,"
echo "the bug is FIXED! 🎉"
echo ""

# Offer continuous monitoring
echo "================================"
echo "Continuous Monitoring (Ctrl+C to stop):"
echo ""
read -p "Start continuous pool monitoring? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Monitoring pool status every 5 seconds..."
    echo "Generate blogs and watch for pool closure..."
    echo ""
    while true; do
        clear
        echo "🔄 Database Pool Monitor - $(date)"
        echo "================================"
        check_pool_status "Real-time check" || true
        echo ""
        echo "Press Ctrl+C to stop monitoring"
        sleep 5
    done
fi

echo ""
echo "Verification script complete!"
