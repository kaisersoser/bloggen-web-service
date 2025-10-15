#!/bin/bash

# =============================================================================
# Health Check Script
# =============================================================================
# Comprehensive health check for production deployment
# Tests all critical endpoints and services
#
# Usage: ./scripts/health-check.sh [backend-url] [frontend-url]
# Example: ./scripts/health-check.sh https://api.example.com https://example.com
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get URLs from arguments or prompt
BACKEND_URL="${1:-}"
FRONTEND_URL="${2:-}"

if [ -z "$BACKEND_URL" ]; then
    read -p "Enter backend URL (e.g., https://api.example.com): " BACKEND_URL
fi

if [ -z "$FRONTEND_URL" ]; then
    read -p "Enter frontend URL (e.g., https://example.com): " FRONTEND_URL
fi

# Remove trailing slashes
BACKEND_URL="${BACKEND_URL%/}"
FRONTEND_URL="${FRONTEND_URL%/}"

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Helper functions
print_header() {
    echo -e "\n${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  $1${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}\n"
}

print_check() {
    echo -e "${BLUE}[CHECK]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
    ((FAILED++))
}

print_warn() {
    echo -e "${YELLOW}[⚠ WARN]${NC} $1"
    ((WARNINGS++))
}

print_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

# Test HTTP endpoint
test_endpoint() {
    local url=$1
    local expected_code=${2:-200}
    local description=$3
    
    print_check "$description"
    
    response=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" "$url" 2>/dev/null || echo "000|0")
    http_code=$(echo $response | cut -d'|' -f1)
    time_total=$(echo $response | cut -d'|' -f2)
    
    if [ "$http_code" = "$expected_code" ]; then
        print_pass "$description - HTTP $http_code (${time_total}s)"
    else
        print_fail "$description - HTTP $http_code (expected $expected_code)"
    fi
}

# Test JSON endpoint
test_json_endpoint() {
    local url=$1
    local description=$2
    local expected_field=$3
    
    print_check "$description"
    
    response=$(curl -s "$url" 2>/dev/null || echo "{}")
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    
    if [ "$http_code" = "200" ]; then
        if [ -n "$expected_field" ]; then
            if echo "$response" | grep -q "\"$expected_field\""; then
                print_pass "$description - HTTP 200, field '$expected_field' present"
                print_info "Response: $(echo $response | head -c 100)..."
            else
                print_warn "$description - HTTP 200, but field '$expected_field' missing"
            fi
        else
            print_pass "$description - HTTP 200"
        fi
    else
        print_fail "$description - HTTP $http_code"
    fi
}

# Start health checks
print_header "PRODUCTION HEALTH CHECK"

echo -e "${CYAN}Checking:${NC}"
echo "  Backend:  $BACKEND_URL"
echo "  Frontend: $FRONTEND_URL"
echo ""

# =============================================================================
# 1. BACKEND HEALTH CHECKS
# =============================================================================
print_header "1. BACKEND HEALTH CHECKS"

test_json_endpoint "$BACKEND_URL/health" "Main health endpoint" "status"

test_json_endpoint "$BACKEND_URL/health/database-pool" "Database pool health" "pool"

print_check "Checking Redis connection..."
response=$(curl -s "$BACKEND_URL/health/redis" 2>/dev/null || echo "{}")
if echo "$response" | grep -q '"status":"healthy"'; then
    print_pass "Redis connection healthy"
else
    print_fail "Redis connection unhealthy or endpoint not available"
fi

# =============================================================================
# 2. FRONTEND HEALTH CHECKS
# =============================================================================
print_header "2. FRONTEND HEALTH CHECKS"

test_endpoint "$FRONTEND_URL" "200" "Homepage loads"

test_endpoint "$FRONTEND_URL/api/auth/signin" "200" "Sign-in page loads"

print_check "Checking static assets..."
response=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL/_next/static/chunks/webpack.js" 2>/dev/null || echo "404")
if [ "$response" = "200" ] || [ "$response" = "304" ]; then
    print_pass "Static assets served correctly"
else
    print_warn "Static assets may not be loading (HTTP $response)"
fi

# =============================================================================
# 3. API ENDPOINTS
# =============================================================================
print_header "3. API ENDPOINTS"

print_check "Testing CORS configuration..."
cors_response=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Origin: $FRONTEND_URL" \
    -H "Access-Control-Request-Method: POST" \
    -X OPTIONS \
    "$BACKEND_URL/api/generate" 2>/dev/null || echo "000")

if [ "$cors_response" = "200" ] || [ "$cors_response" = "204" ]; then
    print_pass "CORS configured correctly"
else
    print_warn "CORS may not be configured (HTTP $cors_response)"
fi

print_check "Testing protected endpoint (should return 401)..."
protected_response=$(curl -s -o /dev/null -w "%{http_code}" \
    "$BACKEND_URL/api/blogs" 2>/dev/null || echo "000")

if [ "$protected_response" = "401" ] || [ "$protected_response" = "403" ]; then
    print_pass "Protected endpoint requires authentication (HTTP $protected_response)"
elif [ "$protected_response" = "200" ]; then
    print_warn "Protected endpoint returned 200 without auth - may be security issue"
else
    print_fail "Protected endpoint returned unexpected code: HTTP $protected_response"
fi

# =============================================================================
# 4. SSL/TLS CHECKS
# =============================================================================
print_header "4. SSL/TLS CHECKS"

print_check "Checking backend SSL certificate..."
backend_ssl=$(echo | openssl s_client -servername "${BACKEND_URL#https://}" -connect "${BACKEND_URL#https://}:443" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "")

if [ -n "$backend_ssl" ]; then
    print_pass "Backend SSL certificate valid"
    print_info "$backend_ssl"
else
    print_warn "Could not verify backend SSL certificate"
fi

print_check "Checking frontend SSL certificate..."
frontend_ssl=$(echo | openssl s_client -servername "${FRONTEND_URL#https://}" -connect "${FRONTEND_URL#https://}:443" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "")

if [ -n "$frontend_ssl" ]; then
    print_pass "Frontend SSL certificate valid"
    print_info "$frontend_ssl"
else
    print_warn "Could not verify frontend SSL certificate"
fi

# =============================================================================
# 5. PERFORMANCE CHECKS
# =============================================================================
print_header "5. PERFORMANCE CHECKS"

print_check "Measuring backend response time..."
backend_time=$(curl -s -o /dev/null -w "%{time_total}" "$BACKEND_URL/health" 2>/dev/null || echo "999")

if (( $(echo "$backend_time < 1.0" | bc -l) )); then
    print_pass "Backend response time: ${backend_time}s (excellent)"
elif (( $(echo "$backend_time < 2.0" | bc -l) )); then
    print_pass "Backend response time: ${backend_time}s (good)"
else
    print_warn "Backend response time: ${backend_time}s (slow, should be < 2s)"
fi

print_check "Measuring frontend response time..."
frontend_time=$(curl -s -o /dev/null -w "%{time_total}" "$FRONTEND_URL" 2>/dev/null || echo "999")

if (( $(echo "$frontend_time < 1.0" | bc -l) )); then
    print_pass "Frontend response time: ${frontend_time}s (excellent)"
elif (( $(echo "$frontend_time < 3.0" | bc -l) )); then
    print_pass "Frontend response time: ${frontend_time}s (good)"
else
    print_warn "Frontend response time: ${frontend_time}s (slow, should be < 3s)"
fi

# =============================================================================
# 6. CONNECTIVITY CHECKS
# =============================================================================
print_header "6. CONNECTIVITY CHECKS"

print_check "Testing DNS resolution..."
backend_host=$(echo "$BACKEND_URL" | sed -e 's|https://||' -e 's|http://||' -e 's|/.*||')
if nslookup "$backend_host" > /dev/null 2>&1; then
    print_pass "Backend DNS resolves correctly"
else
    print_fail "Backend DNS resolution failed"
fi

frontend_host=$(echo "$FRONTEND_URL" | sed -e 's|https://||' -e 's|http://||' -e 's|/.*||')
if nslookup "$frontend_host" > /dev/null 2>&1; then
    print_pass "Frontend DNS resolves correctly"
else
    print_fail "Frontend DNS resolution failed"
fi

# =============================================================================
# SUMMARY
# =============================================================================
print_header "HEALTH CHECK SUMMARY"

echo -e "${BLUE}Checks completed:${NC}"
echo -e "${GREEN}  ✓ Passed:   $PASSED${NC}"
echo -e "${RED}  ✗ Failed:   $FAILED${NC}"
echo -e "${YELLOW}  ⚠ Warnings: $WARNINGS${NC}"

echo ""

# Calculate health score
TOTAL=$((PASSED + FAILED + WARNINGS))
if [ $TOTAL -eq 0 ]; then
    HEALTH_SCORE=0
else
    HEALTH_SCORE=$((PASSED * 100 / TOTAL))
fi

echo -e "${CYAN}Overall Health Score: ${HEALTH_SCORE}%${NC}"

if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║       ✓ ALL HEALTH CHECKS PASSED - SYSTEM HEALTHY!      ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║     ⚠ SYSTEM OPERATIONAL WITH WARNINGS - REVIEW LOGS    ║${NC}"
    echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║    ✗ CRITICAL ISSUES DETECTED - IMMEDIATE ACTION NEEDED  ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}"
    
    echo -e "\n${RED}Recommended actions:${NC}"
    echo "  1. Check Railway logs: railway logs"
    echo "  2. Check Vercel logs: vercel logs"
    echo "  3. Verify environment variables are set correctly"
    echo "  4. Consider rolling back: ./scripts/rollback.sh"
    
    exit 1
fi
