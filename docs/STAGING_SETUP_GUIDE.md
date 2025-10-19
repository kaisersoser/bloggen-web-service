# Staging Environment Setup Guide

## Overview

This guide explains how to set up and use the Windows Docker staging environment for testing changes before deploying to production.

## Prerequisites

✅ **Completed in Milestone 1:**
- Docker Desktop installed and running
- Git installed
- Repository cloned to `D:\User\Projects\bloggen-web-service`

## Configuration

### Step 1: Configure Environment Variables

You need to configure the `.env.staging` files with your actual credentials:

#### Backend Configuration (`backend/.env.staging`)

Open `backend/.env.staging` and update these values:

```bash
# Database - Use production Supabase or create staging database
DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@YOUR_HOST:5432/YOUR_DATABASE"

# Redis - Use production Upstash or local Redis
REDIS_HOST="localhost"
REDIS_PORT=6379

# API Keys - Copy from your production .env
OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE
REPLICATE_API_KEY=YOUR_REPLICATE_API_KEY_HERE
UNSPLASH_ACCESS_KEY=YOUR_UNSPLASH_ACCESS_KEY_HERE

# NextAuth Secret - Generate new with: openssl rand -base64 32
NEXTAUTH_SECRET="staging-secret-change-this-12345678"
```

#### Frontend Configuration (`frontend-nextjs/blog-generator-ui/.env.staging`)

Open `frontend-nextjs/blog-generator-ui/.env.staging` and update these values:

```bash
# Database - Must match backend DATABASE_URL
DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@YOUR_HOST:5432/YOUR_DATABASE"

# Supabase - Use production credentials or create staging project
NEXT_PUBLIC_SUPABASE_URL="https://YOUR_PROJECT.supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY="YOUR_SUPABASE_ANON_KEY"
SUPABASE_SERVICE_ROLE_KEY="YOUR_SUPABASE_SERVICE_ROLE_KEY"

# NextAuth Secret - Must match backend
NEXTAUTH_SECRET="staging-secret-change-this-12345678"

# Google OAuth - Use production credentials or register localhost:3000
GOOGLE_CLIENT_ID="YOUR_GOOGLE_CLIENT_ID"
GOOGLE_CLIENT_SECRET="YOUR_GOOGLE_CLIENT_SECRET"
```

### Step 2: Pull Latest Changes from Feature Branch

```powershell
# Navigate to repository
cd D:\User\Projects\bloggen-web-service

# Pull the staging configuration
git fetch origin
git checkout feature/staging-environment
git pull origin feature/staging-environment
```

## Running Staging Environment

### Start Staging

```powershell
# From repository root
.\scripts\staging-start.ps1
```

This will:
1. ✅ Check Docker is running
2. ✅ Verify .env.staging files exist
3. ✅ Build and start Docker containers
4. ✅ Display service URLs

### Test Staging

```powershell
# Run health checks
.\scripts\staging-test.ps1
```

This will:
1. ✅ Test backend health endpoint
2. ✅ Test frontend accessibility
3. ✅ Show Docker container status
4. ✅ Display test results summary

### Stop Staging

```powershell
# Stop containers (preserve data)
.\scripts\staging-stop.ps1
```

### Clean Staging

```powershell
# Remove all containers, volumes, and images
.\scripts\staging-clean.ps1
```

⚠️ **Warning**: This removes ALL staging data!

## Service URLs

When staging is running:

- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:5000
- **Backend Health**: http://localhost:5000/health

## Testing Workflow

### 1. Basic Functionality Test

1. Open http://localhost:3000 in browser
2. Sign in with Google OAuth
3. Navigate to blog generation page
4. Generate a test blog
5. Verify blog appears in history
6. Check SSE streaming works

### 2. Log Monitoring

```powershell
# View all logs
docker-compose -f docker-compose.staging.yml logs -f

# View backend logs only
docker-compose -f docker-compose.staging.yml logs -f backend-staging

# View frontend logs only
docker-compose -f docker-compose.staging.yml logs -f frontend-staging
```

### 3. Database Verification

```powershell
# Connect to backend container
docker exec -it bloggen-backend-staging /bin/bash

# Check database connection (inside container)
python -c "import psycopg2; conn = psycopg2.connect('YOUR_DATABASE_URL'); print('Connected!')"
```

## Troubleshooting

### Issue: Docker not running

**Error**: "Docker is not running!"

**Solution**: 
1. Open Docker Desktop
2. Wait for Docker to fully start
3. Run `.\scripts\staging-start.ps1` again

### Issue: Port already in use

**Error**: "Bind for 0.0.0.0:3000 failed: port is already allocated"

**Solution**:
1. Stop any local dev servers
2. Run `.\scripts\staging-clean.ps1`
3. Run `.\scripts\staging-start.ps1` again

### Issue: Environment file missing

**Error**: "Missing backend\.env.staging"

**Solution**:
1. Verify you pulled the feature branch
2. Check `.env.staging` files exist
3. Configure environment variables (see Step 1)

### Issue: Health check failing

**Error**: "Backend health check failed"

**Solution**:
1. Check logs: `docker-compose -f docker-compose.staging.yml logs backend-staging`
2. Verify DATABASE_URL is correct
3. Verify API keys are valid
4. Check Redis connection

### Issue: OAuth not working

**Error**: "OAuth sign-in fails"

**Solution**:
1. Verify Google OAuth credentials in `.env.staging`
2. Add http://localhost:3000 as authorized redirect URI in Google Cloud Console
3. Restart staging: `.\scripts\staging-stop.ps1` then `.\scripts\staging-start.ps1`

## Development Workflow

### Testing Changes Before Production

1. **Make changes on Linux dev server** (VSCode Remote SSH)
2. **Commit to feature branch** (do not push to main)
3. **Pull changes to Windows staging**:
   ```powershell
   git fetch origin
   git pull origin feature/staging-environment
   ```
4. **Restart staging**:
   ```powershell
   .\scripts\staging-stop.ps1
   .\scripts\staging-start.ps1
   ```
5. **Run tests**:
   ```powershell
   .\scripts\staging-test.ps1
   ```
6. **Validate functionality** (manual testing)
7. **If tests pass**: Merge to main and deploy to production
8. **If tests fail**: Fix on Linux dev, repeat from step 2

## Quick Reference

| Command | Purpose |
|---------|---------|
| `.\scripts\staging-start.ps1` | Start staging environment |
| `.\scripts\staging-stop.ps1` | Stop staging environment |
| `.\scripts\staging-test.ps1` | Run health checks |
| `.\scripts\staging-clean.ps1` | Clean all staging resources |
| `docker-compose -f docker-compose.staging.yml logs -f` | View logs |
| `docker ps` | Check container status |

## Next Steps

After successfully testing in staging:
1. ✅ Merge feature branch to main (on Linux dev server)
2. ✅ Push to GitHub
3. ✅ Deploy to production (Railway + Vercel auto-deploy)
4. ✅ Verify production deployment
5. ✅ Update documentation if needed

## Support

If you encounter issues:
1. Check logs: `docker-compose -f docker-compose.staging.yml logs`
2. Verify environment configuration
3. Review troubleshooting section above
4. Check Docker Desktop is running properly
