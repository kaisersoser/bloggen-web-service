#!/bin/bash
# Comprehensive Blog Generation Test
# Captures detailed logs from frontend, backend, and pool monitoring

TEST_ID="test_$(date +%Y%m%d_%H%M%S)"
TEST_DIR="test_results_${TEST_ID}"
mkdir -p "$TEST_DIR"

echo "=========================================="
echo "  Comprehensive Blog Generation Test"
echo "  Test ID: $TEST_ID"
echo "  Directory: $TEST_DIR"
echo "=========================================="
echo ""

# Function to capture snapshot
capture_snapshot() {
    local label="$1"
    local timestamp=$(date +%H:%M:%S)
    
    echo "[$timestamp] Capturing snapshot: $label"
    
    # Pool status
    curl -s -k https://localhost:5000/health/database-pool > "$TEST_DIR/pool_${label}.json"
    
    # Backend last 100 lines
    tail -100 backend/backend.log > "$TEST_DIR/backend_${label}.log"
    
    # Frontend last 100 lines
    tail -100 frontend-nextjs/blog-generator-ui/frontend.log > "$TEST_DIR/frontend_${label}.log"
    
    # System health
    curl -s -k https://localhost:5000/health/system > "$TEST_DIR/system_${label}.json"
    
    echo "  Snapshot saved: $label"
}

# Initial snapshot
echo "📸 Taking initial snapshot..."
capture_snapshot "00_initial"

echo ""
echo "=========================================="
echo "🚀 INSTRUCTIONS FOR TESTING:"
echo "=========================================="
echo ""
echo "1. Navigate to: https://localhost:3001"
echo "2. Generate a blog (any topic)"
echo "3. Wait for completion"
echo "4. Come back here and press ENTER"
echo ""
read -p "Press ENTER after first blog is generated..."

# After first blog
echo ""
echo "📸 Capturing snapshot after BLOG 1..."
capture_snapshot "01_after_blog1"
sleep 5

# Check pool status
echo ""
echo "🔍 Checking pool status after Blog 1..."
POOL_STATUS=$(curl -s -k https://localhost:5000/health/database-pool)
CLOSED=$(echo "$POOL_STATUS" | jq -r '.stats.closed')
IN_USE=$(echo "$POOL_STATUS" | jq -r '.stats.in_use')
FREE=$(echo "$POOL_STATUS" | jq -r '.stats.free')

echo "  Pool Status: closed=$CLOSED in_use=$IN_USE free=$FREE"

if [ "$CLOSED" = "true" ]; then
    echo "  🚨 PROBLEM DETECTED: Pool is marked as CLOSED after blog 1!"
fi

# Second blog
echo ""
echo "=========================================="
echo "🚀 GENERATE SECOND BLOG:"
echo "=========================================="
echo ""
echo "Generate a second blog now..."
echo ""
read -p "Press ENTER after second blog is generated (or if it failed)..."

# After second blog
echo ""
echo "📸 Capturing snapshot after BLOG 2 attempt..."
capture_snapshot "02_after_blog2"
sleep 5

# Final analysis
echo ""
echo "=========================================="
echo "📊 FINAL ANALYSIS"
echo "=========================================="
echo ""

# Compare pool states
echo "📈 Pool State Comparison:"
echo ""

for snapshot in 00_initial 01_after_blog1 02_after_blog2; do
    if [ -f "$TEST_DIR/pool_${snapshot}.json" ]; then
        CLOSED=$(jq -r '.stats.closed' "$TEST_DIR/pool_${snapshot}.json")
        IN_USE=$(jq -r '.stats.in_use' "$TEST_DIR/pool_${snapshot}.json")
        FREE=$(jq -r '.stats.free' "$TEST_DIR/pool_${snapshot}.json")
        SIZE=$(jq -r '.stats.size' "$TEST_DIR/pool_${snapshot}.json")
        HEALTHY=$(jq -r '.healthy' "$TEST_DIR/pool_${snapshot}.json")
        
        echo "  $snapshot:"
        echo "    healthy=$HEALTHY closed=$CLOSED in_use=$IN_USE free=$FREE size=$SIZE"
    fi
done

echo ""
echo "🔍 Checking for critical errors..."
echo ""

# Check for pool-related errors in backend
echo "Backend pool errors:"
grep -i "pool.*closed\|connection not available\|pool.*failed" backend/backend.log | tail -10 | sed 's/^/  /'

echo ""
echo "Backend database errors:"
grep -i "database.*error\|database.*failed" backend/backend.log | tail -10 | sed 's/^/  /'

echo ""
echo "=========================================="
echo "✅ TEST COMPLETE"
echo "=========================================="
echo ""
echo "All test results saved to: $TEST_DIR/"
echo ""
echo "Review files:"
echo "  - pool_*.json (pool status snapshots)"
echo "  - backend_*.log (backend log snapshots)"
echo "  - frontend_*.log (frontend log snapshots)"
echo "  - system_*.json (system health snapshots)"
echo ""
