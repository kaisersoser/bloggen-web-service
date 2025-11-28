# Production Deployment Guide

## Overview
This guide walks through deploying the queue system with real-time status updates to production.

## What's Being Deployed

### Code Changes
- **Hybrid state management**: Active blogs tracked in local React state
- **Sequential queue system**: One blog generation at a time
- **Real-time updates**: Status changes without page refresh
- **Enhanced error handling**: Retry logic and failure tracking

### Database Changes
- New columns: `queue_position`, `retry_count`, `max_retries`, `failure_reason`, `last_retry_at`
- New indexes for performance optimization
- Cleanup of stuck IN_PROGRESS blogs

## Pre-Deployment Checklist

- [ ] All tests passing locally
- [ ] No uncommitted changes
- [ ] Backend and frontend running successfully in development
- [ ] Database backup completed (recommended)
- [ ] Supabase dashboard access confirmed

## Deployment Steps

### Option 1: Automated Deployment (Recommended)

```bash
./deploy-to-production.sh
```

The script will:
1. Verify you're on development branch
2. Check for uncommitted changes
3. Merge development → staging
4. Prompt you to run database migration
5. Push to staging (triggers Railway deployment)
6. Merge staging → main (triggers Vercel deployment)

### Option 2: Manual Deployment

#### Step 1: Merge to Staging
```bash
git checkout feature/staging-environment
git pull origin feature/staging-environment
git merge development --no-ff
git push origin feature/staging-environment
```

#### Step 2: Run Database Migration

**On Supabase:**
1. Go to https://supabase.com/dashboard
2. Navigate to your project
3. Open SQL Editor
4. Copy and run: `database/migrations/001_queue_system_migration.sql`
5. Verify results (should show column additions and index creations)

**What the migration does:**
- Adds queue management columns to `blogs` table
- Creates performance indexes
- Resets any stuck IN_PROGRESS blogs to QUEUED
- Adds column comments for documentation

#### Step 3: Deploy to Production
```bash
git checkout main
git pull origin main
git merge feature/staging-environment --no-ff
git push origin main
```

This triggers:
- **Railway**: Backend deployment (automatic)
- **Vercel**: Frontend deployment (automatic)

## Post-Deployment Verification

### 1. Check Deployments
- Railway: https://railway.app (backend logs)
- Vercel: https://vercel.com (frontend logs)

### 2. Test Queue System
1. Submit a blog generation
2. Verify status shows "Queued" immediately
3. Watch status change to "Generating" without refresh
4. Verify completion updates automatically

### 3. Check Database
```sql
-- Verify new columns exist
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'blogs';

-- Check blog statuses
SELECT status, COUNT(*) FROM blogs GROUP BY status;
```

### 4. Monitor Logs
```bash
# Backend (if self-hosted)
tail -f backend/logs/backend.log

# Check for errors
grep -i "error\|exception" backend/logs/backend.log
```

## Rollback Procedure

If issues arise:

### 1. Revert Code
```bash
git checkout main
git revert HEAD
git push origin main
```

### 2. Rollback Database (if needed)
Run `database/migrations/001_queue_system_rollback.sql` in Supabase SQL Editor

**⚠️ WARNING:** This removes queue management columns and data

### 3. Monitor
- Check Railway/Vercel deployments complete
- Verify application works with old code
- Check no database errors

## Troubleshooting

### Issue: Status not updating
**Symptoms:** Blog stays "Queued" even when generating

**Solutions:**
1. Check browser console for errors
2. Verify SSE connection established (Network tab)
3. Check backend logs for queue processing
4. Clear browser cache and reload

### Issue: Database migration fails
**Symptoms:** Column already exists errors

**Solutions:**
1. Check if migration was already run
2. Verify table structure matches expected schema
3. Run rollback script first if needed

### Issue: Multiple blogs generating simultaneously
**Symptoms:** Queue not enforcing one-at-a-time

**Solutions:**
1. Check backend queue manager is running
2. Verify no background_tasks.add_task calls bypassing queue
3. Check Redis connection for queue state

## Environment-Specific Notes

### Development
- Uses local PostgreSQL
- Manual server restarts required
- Hot reload enabled

### Staging (feature/staging-environment)
- Uses Docker Compose
- Connects to test Supabase instance
- Mimics production setup

### Production (main)
- Railway backend (auto-deploy on main push)
- Vercel frontend (auto-deploy on main push)
- Production Supabase database
- HTTPS enforced

## Database Migration Details

### New Schema
```sql
-- Queue management fields
queue_position   INTEGER           -- Position in queue (NULL = not queued)
retry_count      INTEGER NOT NULL  -- Number of retry attempts
max_retries      INTEGER NOT NULL  -- Maximum allowed retries
failure_reason   TEXT              -- Detailed failure message
last_retry_at    TIMESTAMP         -- Last retry timestamp
```

### Indexes Created
```sql
idx_blogs_queue_position           -- For queue ordering
idx_blogs_status_created          -- For status filtering
idx_blogs_user_status_created     -- For user-specific queries
```

## Support Contacts

- **Backend Issues**: Check Railway logs
- **Frontend Issues**: Check Vercel logs  
- **Database Issues**: Check Supabase dashboard
- **Git Issues**: Run `git status` and `git log`

## Additional Resources

- [Git Workflow Documentation](docs/DEPLOYMENT.md)
- [Queue System Architecture](docs/ASYNC_QUEUE_DESIGN_PLAN.md)
- [Database Schema](frontend-nextjs/blog-generator-ui/prisma/schema.prisma)
