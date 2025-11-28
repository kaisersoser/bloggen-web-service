#!/bin/bash
set -e

echo "🚀 Production Deployment Script"
echo "================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check current branch
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 Current branch: $CURRENT_BRANCH"

if [ "$CURRENT_BRANCH" != "development" ]; then
    echo -e "${RED}❌ Must be on development branch to deploy${NC}"
    exit 1
fi

# Check for uncommitted changes
if [[ -n $(git status -s) ]]; then
    echo -e "${RED}❌ You have uncommitted changes. Commit or stash them first.${NC}"
    git status -s
    exit 1
fi

echo ""
echo "Step 1: Merge development → feature/staging-environment"
echo "--------------------------------------------------------"
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 1
fi

git checkout feature/staging-environment
git pull origin feature/staging-environment
git merge development --no-ff -m "chore: merge development changes for production deployment

- Hybrid state management for real-time blog status updates
- Active blogs tracked in local state for instant UI updates
- Fixed React Query cache notification issues
- Enhanced logging for debugging state changes"

echo -e "${GREEN}✅ Merged into staging${NC}"

echo ""
echo "Step 2: Run database migration on Supabase"
echo "-------------------------------------------"
echo -e "${YELLOW}⚠️  MANUAL STEP REQUIRED:${NC}"
echo ""
echo "1. Go to your Supabase dashboard: https://supabase.com/dashboard"
echo "2. Navigate to your project → SQL Editor"
echo "3. Run the migration script: database/migrations/001_queue_system_migration.sql"
echo "4. Verify the migration completed successfully"
echo ""
echo "Migration script adds:"
echo "  - queue_position column (for queue management)"
echo "  - retry_count, max_retries columns (for retry logic)"
echo "  - failure_reason, last_retry_at columns (for error tracking)"
echo "  - Indexes for performance optimization"
echo "  - Resets any stuck IN_PROGRESS blogs to QUEUED"
echo ""
read -p "Have you run the migration successfully? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}❌ Please run the migration before continuing${NC}"
    exit 1
fi

echo ""
echo "Step 3: Push staging branch to trigger Railway deployment"
echo "---------------------------------------------------------"
read -p "Push to remote and trigger production deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 1
fi

git push origin feature/staging-environment

echo -e "${GREEN}✅ Pushed to staging${NC}"

echo ""
echo "Step 4: Merge staging → main (production)"
echo "------------------------------------------"
read -p "Merge to main branch for production? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Stopping before main branch merge."
    echo "You can manually merge later with:"
    echo "  git checkout main"
    echo "  git merge feature/staging-environment --no-ff"
    exit 0
fi

git checkout main
git pull origin main
git merge feature/staging-environment --no-ff -m "release: deploy queue system with real-time status updates

Production deployment includes:
- Sequential blog generation queue system
- Real-time status updates without page refresh
- Hybrid state management (activeBlogs + persistedBlogs)
- Enhanced error handling and retry logic
- Database schema updates for queue management

Migration required: database/migrations/001_queue_system_migration.sql"

git push origin main

echo ""
echo -e "${GREEN}🎉 Production Deployment Complete!${NC}"
echo ""
echo "Deployment Summary:"
echo "  - Staging branch: ✅ Updated and pushed"
echo "  - Database migration: ✅ Applied to Supabase"
echo "  - Production (main): ✅ Merged and pushed"
echo ""
echo "Next Steps:"
echo "  1. Monitor Railway deployment: https://railway.app"
echo "  2. Monitor Vercel deployment: https://vercel.com"
echo "  3. Test production: https://your-production-url.vercel.app"
echo "  4. Watch for errors in logs"
echo ""
echo "Switch back to development branch:"
echo "  git checkout development"
