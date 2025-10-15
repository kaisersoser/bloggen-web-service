#!/bin/bash

# =============================================================================
# Production Deployment Script
# =============================================================================
# Automated deployment to Railway (backend) and Vercel (frontend)
# This script handles the complete deployment workflow
#
# Usage: ./scripts/deploy-production.sh [--skip-checks] [--backend-only] [--frontend-only]
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse arguments
SKIP_CHECKS=false
BACKEND_ONLY=false
FRONTEND_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-checks)
            SKIP_CHECKS=true
            shift
            ;;
        --backend-only)
            BACKEND_ONLY=true
            shift
            ;;
        --frontend-only)
            FRONTEND_ONLY=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-checks] [--backend-only] [--frontend-only]"
            exit 1
            ;;
    esac
done

# Helper functions
print_header() {
    echo -e "\n${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  $1${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}\n"
}

print_step() {
    echo -e "\n${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

# Confirm deployment
print_header "PRODUCTION DEPLOYMENT SCRIPT"

echo -e "${YELLOW}⚠️  WARNING: You are about to deploy to PRODUCTION${NC}"
echo ""
echo "This will:"
if [ "$BACKEND_ONLY" = false ]; then
    echo "  • Deploy backend to Railway"
fi
if [ "$FRONTEND_ONLY" = false ]; then
    echo "  • Deploy frontend to Vercel"
fi
echo "  • Use production environment variables"
echo "  • Affect live users (if already deployed)"
echo ""

read -p "Are you sure you want to continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# =============================================================================
# STEP 1: PRE-DEPLOYMENT CHECKS
# =============================================================================
if [ "$SKIP_CHECKS" = false ]; then
    print_header "STEP 1: PRE-DEPLOYMENT CHECKS"
    
    if [ -f "./scripts/pre-deploy-check.sh" ]; then
        print_step "Running pre-deployment checks..."
        bash ./scripts/pre-deploy-check.sh
        
        if [ $? -ne 0 ]; then
            print_error "Pre-deployment checks failed. Fix issues and try again."
            exit 1
        fi
        print_success "Pre-deployment checks passed"
    else
        print_warning "Pre-deployment check script not found. Skipping checks."
    fi
else
    print_warning "Skipping pre-deployment checks (--skip-checks flag)"
fi

# =============================================================================
# STEP 2: CHECK REQUIRED TOOLS
# =============================================================================
print_header "STEP 2: CHECKING REQUIRED TOOLS"

print_step "Checking for required CLI tools..."

# Check Git
if command -v git &> /dev/null; then
    print_success "Git installed: $(git --version)"
else
    print_error "Git not found. Please install Git."
    exit 1
fi

# Check Railway CLI (if deploying backend)
if [ "$FRONTEND_ONLY" = false ]; then
    if command -v railway &> /dev/null; then
        print_success "Railway CLI installed: $(railway --version)"
    else
        print_warning "Railway CLI not found. Deploying via git push."
        print_info "Install Railway CLI for better control: npm install -g @railway/cli"
    fi
fi

# Check Vercel CLI (if deploying frontend)
if [ "$BACKEND_ONLY" = false ]; then
    if command -v vercel &> /dev/null; then
        print_success "Vercel CLI installed: $(vercel --version)"
    else
        print_warning "Vercel CLI not found. Deploying via git push."
        print_info "Install Vercel CLI for better control: npm install -g vercel"
    fi
fi

# =============================================================================
# STEP 3: GIT OPERATIONS
# =============================================================================
print_header "STEP 3: GIT OPERATIONS"

print_step "Checking git status..."

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    print_warning "Uncommitted changes detected."
    echo ""
    git status --short
    echo ""
    
    read -p "Do you want to commit these changes? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        read -p "Enter commit message: " COMMIT_MSG
        git add .
        git commit -m "$COMMIT_MSG"
        print_success "Changes committed"
    else
        print_warning "Deploying with uncommitted changes (not recommended)"
    fi
else
    print_success "No uncommitted changes"
fi

# Push to remote
print_step "Pushing to remote repository..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
print_info "Current branch: $CURRENT_BRANCH"

git push origin $CURRENT_BRANCH
print_success "Pushed to origin/$CURRENT_BRANCH"

# =============================================================================
# STEP 4: BACKEND DEPLOYMENT (Railway)
# =============================================================================
if [ "$FRONTEND_ONLY" = false ]; then
    print_header "STEP 4: BACKEND DEPLOYMENT (Railway)"
    
    cd backend
    
    # Check if Railway is configured
    if command -v railway &> /dev/null; then
        print_step "Deploying backend to Railway via CLI..."
        
        # Check if logged in
        if railway whoami &> /dev/null; then
            print_success "Railway authenticated"
        else
            print_warning "Not logged in to Railway. Logging in..."
            railway login
        fi
        
        # Deploy
        print_step "Starting Railway deployment..."
        railway up --detach
        
        if [ $? -eq 0 ]; then
            print_success "Backend deployed to Railway"
            
            # Get deployment URL
            BACKEND_URL=$(railway domain 2>/dev/null || echo "Check Railway dashboard for URL")
            print_info "Backend URL: $BACKEND_URL"
        else
            print_error "Railway deployment failed"
            exit 1
        fi
    else
        print_step "Railway CLI not available. Deploying via git push..."
        print_info "Railway will auto-deploy from GitHub push"
        print_warning "Monitor deployment in Railway dashboard: https://railway.app/dashboard"
    fi
    
    cd ..
else
    print_warning "Skipping backend deployment (--frontend-only flag)"
fi

# =============================================================================
# STEP 5: FRONTEND DEPLOYMENT (Vercel)
# =============================================================================
if [ "$BACKEND_ONLY" = false ]; then
    print_header "STEP 5: FRONTEND DEPLOYMENT (Vercel)"
    
    cd frontend-nextjs/blog-generator-ui
    
    # Check if Vercel is configured
    if command -v vercel &> /dev/null; then
        print_step "Deploying frontend to Vercel via CLI..."
        
        # Check if logged in
        if vercel whoami &> /dev/null; then
            print_success "Vercel authenticated"
        else
            print_warning "Not logged in to Vercel. Logging in..."
            vercel login
        fi
        
        # Deploy to production
        print_step "Starting Vercel deployment..."
        vercel --prod --yes
        
        if [ $? -eq 0 ]; then
            print_success "Frontend deployed to Vercel"
            
            # Get deployment URL
            FRONTEND_URL=$(vercel inspect --prod 2>/dev/null | grep "URL:" | awk '{print $2}' || echo "Check Vercel dashboard for URL")
            print_info "Frontend URL: $FRONTEND_URL"
        else
            print_error "Vercel deployment failed"
            exit 1
        fi
    else
        print_step "Vercel CLI not available. Deploying via git push..."
        print_info "Vercel will auto-deploy from GitHub push"
        print_warning "Monitor deployment in Vercel dashboard: https://vercel.com/dashboard"
    fi
    
    cd ../..
else
    print_warning "Skipping frontend deployment (--backend-only flag)"
fi

# =============================================================================
# STEP 6: POST-DEPLOYMENT VERIFICATION
# =============================================================================
print_header "STEP 6: POST-DEPLOYMENT VERIFICATION"

print_step "Waiting for deployments to complete (30 seconds)..."
sleep 30

# Health check backend
if [ "$FRONTEND_ONLY" = false ]; then
    print_step "Checking backend health..."
    
    if [ -n "$BACKEND_URL" ] && [ "$BACKEND_URL" != "Check Railway dashboard for URL" ]; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health" || echo "000")
        
        if [ "$HTTP_CODE" = "200" ]; then
            print_success "Backend health check passed (HTTP $HTTP_CODE)"
        else
            print_error "Backend health check failed (HTTP $HTTP_CODE)"
            print_warning "Check Railway logs: railway logs"
        fi
    else
        print_warning "Backend URL not available. Check Railway dashboard manually."
    fi
fi

# Health check frontend
if [ "$BACKEND_ONLY" = false ]; then
    print_step "Checking frontend health..."
    
    if [ -n "$FRONTEND_URL" ] && [ "$FRONTEND_URL" != "Check Vercel dashboard for URL" ]; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" || echo "000")
        
        if [ "$HTTP_CODE" = "200" ]; then
            print_success "Frontend health check passed (HTTP $HTTP_CODE)"
        else
            print_error "Frontend health check failed (HTTP $HTTP_CODE)"
            print_warning "Check Vercel logs: vercel logs"
        fi
    else
        print_warning "Frontend URL not available. Check Vercel dashboard manually."
    fi
fi

# =============================================================================
# STEP 7: SUMMARY
# =============================================================================
print_header "DEPLOYMENT SUMMARY"

echo -e "${GREEN}Deployment completed successfully! 🎉${NC}"
echo ""

if [ "$FRONTEND_ONLY" = false ]; then
    echo -e "${CYAN}Backend (Railway):${NC}"
    echo "  • URL: $BACKEND_URL"
    echo "  • Dashboard: https://railway.app/dashboard"
    echo "  • Logs: railway logs"
    echo ""
fi

if [ "$BACKEND_ONLY" = false ]; then
    echo -e "${CYAN}Frontend (Vercel):${NC}"
    echo "  • URL: $FRONTEND_URL"
    echo "  • Dashboard: https://vercel.com/dashboard"
    echo "  • Logs: vercel logs"
    echo ""
fi

echo -e "${CYAN}Next Steps:${NC}"
echo "  1. Verify application works end-to-end"
echo "  2. Test user registration and login"
echo "  3. Generate a test blog"
echo "  4. Monitor logs for any errors"
echo "  5. Set up monitoring alerts"
echo ""

echo -e "${YELLOW}Important:${NC}"
echo "  • Keep monitoring for the next 30 minutes"
echo "  • If issues occur, run: ./scripts/rollback.sh"
echo "  • Check health endpoints regularly"
echo ""

print_success "Deployment script completed!"

# Save deployment info
DEPLOYMENT_LOG="deployments/deployment-$(date +%Y%m%d-%H%M%S).log"
mkdir -p deployments
cat > "$DEPLOYMENT_LOG" << EOF
Deployment Log
==============
Date: $(date)
Branch: $CURRENT_BRANCH
Commit: $(git rev-parse HEAD)
Backend URL: $BACKEND_URL
Frontend URL: $FRONTEND_URL

Deployed Services:
$([ "$FRONTEND_ONLY" = false ] && echo "  - Backend (Railway)")
$([ "$BACKEND_ONLY" = false ] && echo "  - Frontend (Vercel)")

Status: SUCCESS
EOF

print_info "Deployment log saved to: $DEPLOYMENT_LOG"
