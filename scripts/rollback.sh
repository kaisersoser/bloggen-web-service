#!/bin/bash

# =============================================================================
# Rollback Script
# =============================================================================
# Rolls back to previous deployment if issues are detected
# Supports Railway and Vercel rollbacks
#
# Usage: ./scripts/rollback.sh [--backend] [--frontend] [--to-commit HASH]
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse arguments
BACKEND_ROLLBACK=true
FRONTEND_ROLLBACK=true
TARGET_COMMIT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --backend)
            FRONTEND_ROLLBACK=false
            shift
            ;;
        --frontend)
            BACKEND_ROLLBACK=false
            shift
            ;;
        --to-commit)
            TARGET_COMMIT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--backend] [--frontend] [--to-commit HASH]"
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

# Warning
print_header "PRODUCTION ROLLBACK SCRIPT"

echo -e "${YELLOW}⚠️  WARNING: You are about to ROLLBACK production${NC}"
echo ""
echo "This will:"
if [ "$BACKEND_ROLLBACK" = true ]; then
    echo "  • Rollback backend to previous deployment"
fi
if [ "$FRONTEND_ROLLBACK" = true ]; then
    echo "  • Rollback frontend to previous deployment"
fi
echo "  • Affect live users immediately"
echo ""

read -p "Are you sure you want to rollback? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Rollback cancelled."
    exit 0
fi

# =============================================================================
# STEP 1: IDENTIFY TARGET VERSION
# =============================================================================
print_header "STEP 1: IDENTIFY TARGET VERSION"

if [ -z "$TARGET_COMMIT" ]; then
    print_step "Showing recent deployments..."
    
    # Check if deployment log exists
    if [ -d "deployments" ] && [ "$(ls -A deployments 2>/dev/null)" ]; then
        print_info "Recent deployments:"
        ls -lt deployments/ | head -n 6
        echo ""
        
        read -p "Enter deployment log filename (or 'git' to use git history): " DEPLOYMENT_FILE
        
        if [ "$DEPLOYMENT_FILE" = "git" ]; then
            print_step "Showing recent commits..."
            git log --oneline -10
            echo ""
            read -p "Enter commit hash to rollback to: " TARGET_COMMIT
        else
            if [ -f "deployments/$DEPLOYMENT_FILE" ]; then
                TARGET_COMMIT=$(grep "Commit:" "deployments/$DEPLOYMENT_FILE" | awk '{print $2}')
                print_info "Found commit in deployment log: $TARGET_COMMIT"
            else
                print_error "Deployment file not found: $DEPLOYMENT_FILE"
                exit 1
            fi
        fi
    else
        print_warning "No deployment logs found. Using git history..."
        git log --oneline -10
        echo ""
        read -p "Enter commit hash to rollback to: " TARGET_COMMIT
    fi
fi

# Validate commit exists
if ! git rev-parse --verify "$TARGET_COMMIT" > /dev/null 2>&1; then
    print_error "Invalid commit hash: $TARGET_COMMIT"
    exit 1
fi

print_success "Target commit validated: $TARGET_COMMIT"

# Show commit details
print_info "Commit details:"
git show --stat "$TARGET_COMMIT" | head -n 10

echo ""
read -p "Confirm rollback to this commit? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Rollback cancelled."
    exit 0
fi

# =============================================================================
# STEP 2: CREATE SAFETY BACKUP
# =============================================================================
print_header "STEP 2: CREATE SAFETY BACKUP"

print_step "Creating backup of current state..."

CURRENT_COMMIT=$(git rev-parse HEAD)
BACKUP_BRANCH="backup-rollback-$(date +%Y%m%d-%H%M%S)"

git branch "$BACKUP_BRANCH"
print_success "Created backup branch: $BACKUP_BRANCH"
print_info "Current state saved at: $CURRENT_COMMIT"

# =============================================================================
# STEP 3: PERFORM ROLLBACK
# =============================================================================
print_header "STEP 3: PERFORM GIT ROLLBACK"

print_step "Rolling back codebase..."

# Create rollback commit (safer than hard reset)
git revert --no-commit "$CURRENT_COMMIT".."$TARGET_COMMIT"
git commit -m "Rollback to $TARGET_COMMIT from $CURRENT_COMMIT"

print_success "Codebase rolled back"

# Push to remote
print_step "Pushing rollback to remote..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
git push origin $CURRENT_BRANCH

print_success "Pushed to origin/$CURRENT_BRANCH"

# =============================================================================
# STEP 4: BACKEND ROLLBACK (Railway)
# =============================================================================
if [ "$BACKEND_ROLLBACK" = true ]; then
    print_header "STEP 4: BACKEND ROLLBACK (Railway)"
    
    if command -v railway &> /dev/null; then
        cd backend
        
        print_step "Triggering Railway deployment..."
        railway up --detach
        
        if [ $? -eq 0 ]; then
            print_success "Backend rollback initiated on Railway"
        else
            print_error "Railway deployment failed"
            print_warning "Manual intervention required in Railway dashboard"
        fi
        
        cd ..
    else
        print_warning "Railway CLI not available"
        print_info "Railway will auto-deploy from git push"
        print_info "Monitor: https://railway.app/dashboard"
    fi
fi

# =============================================================================
# STEP 5: FRONTEND ROLLBACK (Vercel)
# =============================================================================
if [ "$FRONTEND_ROLLBACK" = true ]; then
    print_header "STEP 5: FRONTEND ROLLBACK (Vercel)"
    
    if command -v vercel &> /dev/null; then
        cd frontend-nextjs/blog-generator-ui
        
        print_step "Triggering Vercel deployment..."
        vercel --prod --yes
        
        if [ $? -eq 0 ]; then
            print_success "Frontend rollback initiated on Vercel"
        else
            print_error "Vercel deployment failed"
            print_warning "Manual intervention required in Vercel dashboard"
        fi
        
        cd ../..
    else
        print_warning "Vercel CLI not available"
        print_info "Vercel will auto-deploy from git push"
        print_info "Monitor: https://vercel.com/dashboard"
    fi
fi

# =============================================================================
# STEP 6: VERIFY ROLLBACK
# =============================================================================
print_header "STEP 6: VERIFY ROLLBACK"

print_step "Waiting for deployments to complete (30 seconds)..."
sleep 30

print_step "Running health checks..."
if [ -f "./scripts/health-check.sh" ]; then
    print_info "Waiting additional 30 seconds for full deployment..."
    sleep 30
    
    read -p "Enter backend URL: " BACKEND_URL
    read -p "Enter frontend URL: " FRONTEND_URL
    
    bash ./scripts/health-check.sh "$BACKEND_URL" "$FRONTEND_URL"
else
    print_warning "Health check script not found. Manual verification required."
fi

# =============================================================================
# STEP 7: SUMMARY
# =============================================================================
print_header "ROLLBACK SUMMARY"

echo -e "${GREEN}Rollback completed! 🔄${NC}"
echo ""

echo -e "${CYAN}Rollback Details:${NC}"
echo "  • From commit: $CURRENT_COMMIT"
echo "  • To commit:   $TARGET_COMMIT"
echo "  • Backup branch: $BACKUP_BRANCH"
echo ""

if [ "$BACKEND_ROLLBACK" = true ]; then
    echo -e "${CYAN}Backend (Railway):${NC}"
    echo "  • Rolled back to previous version"
    echo "  • Monitor: https://railway.app/dashboard"
    echo ""
fi

if [ "$FRONTEND_ROLLBACK" = true ]; then
    echo -e "${CYAN}Frontend (Vercel):${NC}"
    echo "  • Rolled back to previous version"
    echo "  • Monitor: https://vercel.com/dashboard"
    echo ""
fi

echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Verify application works correctly"
echo "  2. Monitor logs for any issues"
echo "  3. Investigate what caused the need to rollback"
echo "  4. Fix issues in a separate branch"
echo "  5. Test thoroughly before redeploying"
echo ""

echo -e "${CYAN}To restore current version later:${NC}"
echo "  git checkout $BACKUP_BRANCH"
echo "  git push origin $CURRENT_BRANCH --force"
echo ""

print_success "Rollback script completed!"

# Save rollback log
ROLLBACK_LOG="rollbacks/rollback-$(date +%Y%m%d-%H%M%S).log"
mkdir -p rollbacks
cat > "$ROLLBACK_LOG" << EOF
Rollback Log
============
Date: $(date)
From Commit: $CURRENT_COMMIT
To Commit: $TARGET_COMMIT
Backup Branch: $BACKUP_BRANCH
Branch: $CURRENT_BRANCH

Rolled Back Services:
$([ "$BACKEND_ROLLBACK" = true ] && echo "  - Backend (Railway)")
$([ "$FRONTEND_ROLLBACK" = true ] && echo "  - Frontend (Vercel)")

Reason: Manual rollback requested
Status: COMPLETED
EOF

print_info "Rollback log saved to: $ROLLBACK_LOG"
