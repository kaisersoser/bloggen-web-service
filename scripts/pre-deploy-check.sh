#!/bin/bash

# =============================================================================
# Pre-Deployment Checker
# =============================================================================
# This script verifies that your application is ready for production deployment
# Run this BEFORE deploying to catch issues early
#
# Usage: ./scripts/pre-deploy-check.sh
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Helper functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
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
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Start checks
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     PRE-DEPLOYMENT CHECKER FOR BLOGGEN WEB SERVICE       ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"

# =============================================================================
# 1. GIT REPOSITORY CHECKS
# =============================================================================
print_header "1. GIT REPOSITORY CHECKS"

print_check "Checking if in git repository..."
if git rev-parse --git-dir > /dev/null 2>&1; then
    print_pass "In git repository"
else
    print_fail "Not in a git repository"
    exit 1
fi

print_check "Checking for uncommitted changes..."
if git diff-index --quiet HEAD --; then
    print_pass "No uncommitted changes"
else
    print_warn "Uncommitted changes detected. Commit before deploying."
    git status --short
fi

print_check "Checking current branch..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
print_info "Current branch: $CURRENT_BRANCH"
if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
    print_pass "On main/master branch"
else
    print_warn "Not on main/master branch. Production typically deploys from main."
fi

print_check "Checking if branch is up to date with remote..."
git fetch origin $CURRENT_BRANCH > /dev/null 2>&1
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "")
if [ -n "$REMOTE" ]; then
    if [ "$LOCAL" = "$REMOTE" ]; then
        print_pass "Branch is up to date with remote"
    else
        print_warn "Branch is not in sync with remote. Pull or push changes."
    fi
else
    print_warn "No remote tracking branch configured"
fi

# =============================================================================
# 2. BACKEND CHECKS
# =============================================================================
print_header "2. BACKEND CHECKS"

cd backend 2>/dev/null || { print_fail "backend/ directory not found"; exit 1; }

print_check "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_info "Python version: $PYTHON_VERSION"
    if [[ "$PYTHON_VERSION" > "3.11" ]] || [[ "$PYTHON_VERSION" = "3.11"* ]]; then
        print_pass "Python 3.11+ installed"
    else
        print_fail "Python 3.11+ required, found $PYTHON_VERSION"
    fi
else
    print_fail "Python 3 not found"
fi

print_check "Checking virtual environment..."
if [ -d ".venv" ]; then
    print_pass "Virtual environment exists"
else
    print_fail "Virtual environment not found. Run: python -m venv .venv"
fi

print_check "Checking requirements.txt..."
if [ -f "requirements.txt" ]; then
    print_pass "requirements.txt exists"
    print_info "Dependencies: $(wc -l < requirements.txt) packages"
else
    print_fail "requirements.txt not found"
fi

print_check "Checking Dockerfile..."
if [ -f "Dockerfile" ]; then
    print_pass "Dockerfile exists"
else
    print_warn "Dockerfile not found. Will create during deployment."
fi

print_check "Checking environment file examples..."
if [ -f ".env.local.example" ]; then
    print_pass ".env.local.example exists"
else
    print_warn ".env.local.example not found"
fi

if [ -f ".env.production.example" ]; then
    print_pass ".env.production.example exists"
else
    print_warn ".env.production.example not found"
fi

print_check "Checking for production secrets in code..."
if grep -r "sk-" --include="*.py" src/ 2>/dev/null | grep -v ".env" | grep -v "example"; then
    print_fail "Hardcoded secrets found in source code!"
else
    print_pass "No hardcoded secrets detected"
fi

print_check "Checking critical files..."
CRITICAL_FILES=(
    "src/main.py"
    "src/api.py"
    "src/core/database_service.py"
    "src/core/redis_manager.py"
    "src/bloggen/flows.py"
)
for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_pass "✓ $file"
    else
        print_fail "✗ $file missing"
    fi
done

print_check "Checking for syntax errors..."
if command -v python3 &> /dev/null; then
    ERROR_COUNT=0
    for file in $(find src -name "*.py" 2>/dev/null); do
        if ! python3 -m py_compile "$file" 2>/dev/null; then
            print_fail "Syntax error in $file"
            ((ERROR_COUNT++))
        fi
    done
    if [ $ERROR_COUNT -eq 0 ]; then
        print_pass "No Python syntax errors detected"
    fi
fi

cd ..

# =============================================================================
# 3. FRONTEND CHECKS
# =============================================================================
print_header "3. FRONTEND CHECKS"

cd frontend-nextjs/blog-generator-ui 2>/dev/null || { print_fail "frontend directory not found"; exit 1; }

print_check "Checking Node.js version..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | cut -d'v' -f2)
    print_info "Node.js version: $NODE_VERSION"
    if [[ "$NODE_VERSION" > "18.0" ]]; then
        print_pass "Node.js 18+ installed"
    else
        print_fail "Node.js 18+ required, found $NODE_VERSION"
    fi
else
    print_fail "Node.js not found"
fi

print_check "Checking package.json..."
if [ -f "package.json" ]; then
    print_pass "package.json exists"
else
    print_fail "package.json not found"
fi

print_check "Checking node_modules..."
if [ -d "node_modules" ]; then
    print_pass "node_modules exists"
else
    print_warn "node_modules not found. Run: npm install"
fi

print_check "Checking Next.js configuration..."
if [ -f "next.config.js" ] || [ -f "next.config.mjs" ]; then
    print_pass "Next.js config exists"
else
    print_fail "next.config.js not found"
fi

print_check "Checking Prisma schema..."
if [ -f "prisma/schema.prisma" ]; then
    print_pass "Prisma schema exists"
else
    print_fail "Prisma schema not found"
fi

print_check "Checking environment file examples..."
if [ -f ".env.local.example" ]; then
    print_pass ".env.local.example exists"
else
    print_warn ".env.local.example not found"
fi

if [ -f ".env.production.example" ]; then
    print_pass ".env.production.example exists"
else
    print_warn ".env.production.example not found"
fi

print_check "Checking for production secrets in code..."
if grep -r "AKIA" --include="*.ts" --include="*.tsx" --include="*.js" src/ 2>/dev/null; then
    print_fail "Hardcoded AWS keys found in source code!"
else
    print_pass "No hardcoded AWS secrets detected"
fi

print_check "Checking critical files..."
CRITICAL_FILES=(
    "src/app/layout.tsx"
    "src/app/page.tsx"
    "src/app/api/auth/[...nextauth]/route.ts"
    "prisma/schema.prisma"
)
for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_pass "✓ $file"
    else
        print_fail "✗ $file missing"
    fi
done

print_check "Checking build configuration..."
if [ -f "package.json" ]; then
    if grep -q '"build":' package.json; then
        print_pass "Build script configured"
    else
        print_fail "No build script in package.json"
    fi
fi

cd ../..

# =============================================================================
# 4. DEPENDENCY CHECKS
# =============================================================================
print_header "4. DEPENDENCY CHECKS"

print_check "Checking for outdated critical dependencies..."
cd backend
if [ -f "requirements.txt" ]; then
    if grep -q "fastapi" requirements.txt; then
        print_pass "FastAPI dependency found"
    else
        print_warn "FastAPI not in requirements.txt"
    fi
    
    if grep -q "crewai" requirements.txt; then
        print_pass "CrewAI dependency found"
    else
        print_warn "CrewAI not in requirements.txt"
    fi
    
    if grep -q "redis" requirements.txt; then
        print_pass "Redis dependency found"
    else
        print_warn "Redis not in requirements.txt"
    fi
fi
cd ..

cd frontend-nextjs/blog-generator-ui
if [ -f "package.json" ]; then
    if grep -q '"next":' package.json; then
        print_pass "Next.js dependency found"
    else
        print_fail "Next.js not in package.json"
    fi
    
    if grep -q '"next-auth":' package.json; then
        print_pass "NextAuth dependency found"
    else
        print_warn "NextAuth not in package.json"
    fi
fi
cd ../..

# =============================================================================
# 5. CONFIGURATION CHECKS
# =============================================================================
print_header "5. CONFIGURATION CHECKS"

print_check "Checking .gitignore..."
if [ -f ".gitignore" ]; then
    print_pass ".gitignore exists"
    
    if grep -q ".env.local" .gitignore; then
        print_pass ".env.local in .gitignore"
    else
        print_warn ".env.local not in .gitignore - secrets could be exposed!"
    fi
    
    if grep -q ".env.production" .gitignore; then
        print_pass ".env.production in .gitignore"
    else
        print_warn ".env.production not in .gitignore - secrets could be exposed!"
    fi
else
    print_fail ".gitignore not found"
fi

print_check "Checking for sensitive files in git..."
SENSITIVE_FILES=(
    ".env"
    ".env.local"
    ".env.production"
    "backend/.env"
    "backend/.env.local"
    "backend/.env.production"
)
for file in "${SENSITIVE_FILES[@]}"; do
    if git ls-files --error-unmatch "$file" 2>/dev/null; then
        print_fail "Sensitive file tracked by git: $file"
    fi
done
print_pass "No sensitive files tracked by git"

# =============================================================================
# 6. DOCKER CHECKS
# =============================================================================
print_header "6. DOCKER CHECKS"

print_check "Checking for Dockerfiles..."
if [ -f "backend/Dockerfile" ]; then
    print_pass "Backend Dockerfile exists"
else
    print_warn "Backend Dockerfile not found (will be created during deployment)"
fi

if [ -f "frontend-nextjs/blog-generator-ui/Dockerfile" ]; then
    print_pass "Frontend Dockerfile exists"
else
    print_warn "Frontend Dockerfile not found (optional for Vercel)"
fi

# =============================================================================
# 7. DOCUMENTATION CHECKS
# =============================================================================
print_header "7. DOCUMENTATION CHECKS"

print_check "Checking for documentation..."
DOCS=(
    "README.md"
    "docs/DEPLOYMENT_GUIDE.md"
    "docs/ENVIRONMENT_CONFIGURATION.md"
    "PRODUCTION_DEPLOYMENT_PROPOSAL.md"
)
for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        print_pass "✓ $doc"
    else
        print_warn "✗ $doc missing"
    fi
done

# =============================================================================
# SUMMARY
# =============================================================================
print_header "SUMMARY"

echo -e "${BLUE}Checks completed:${NC}"
echo -e "${GREEN}  ✓ Passed:   $PASSED${NC}"
echo -e "${RED}  ✗ Failed:   $FAILED${NC}"
echo -e "${YELLOW}  ⚠ Warnings: $WARNINGS${NC}"

echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ ALL CRITICAL CHECKS PASSED - READY FOR DEPLOYMENT!   ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    
    if [ $WARNINGS -gt 0 ]; then
        echo -e "\n${YELLOW}Note: $WARNINGS warning(s) detected. Review before deploying.${NC}"
    fi
    
    echo -e "\n${BLUE}Next steps:${NC}"
    echo "  1. Review any warnings above"
    echo "  2. Run: ./scripts/deploy-production.sh"
    echo "  3. Monitor deployment in Railway and Vercel dashboards"
    
    exit 0
else
    echo -e "${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ✗ CRITICAL ISSUES DETECTED - FIX BEFORE DEPLOYING!      ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}"
    
    echo -e "\n${RED}Fix the failed checks above before attempting deployment.${NC}"
    
    exit 1
fi
