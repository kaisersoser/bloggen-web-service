# Development Pipeline Implementation Plan
## Windows Docker Staging + Production Deployment

**Document Version**: 1.0  
**Date**: October 18, 2025  
**Status**: Planning Phase  
**Estimated Total Time**: 2-3 hours

---

## 🎯 Executive Summary

This plan establishes a simple, robust development pipeline:

```
Linux Dev Server (VSCode Remote) 
    ↓
Windows Docker Staging (Local Testing)
    ↓
Production (Railway + Vercel)
```

**Key Benefits:**
- ✅ Test production-like environment before deploying
- ✅ No additional cloud costs
- ✅ Catch environment-specific issues early
- ✅ Easy rollback capability
- ✅ Maintains single production system

---

## 📋 Prerequisites

### Required Software (Windows)
- [ ] Docker Desktop for Windows (latest version)
- [ ] Git for Windows
- [ ] PowerShell 7+ (recommended) or Command Prompt
- [ ] Web browser for testing

### Required Access
- [ ] SSH access to Linux dev server (already have)
- [ ] GitHub repository access (already have)
- [ ] Railway account access (already have)
- [ ] Vercel account access (already have)

### Required Files
- [ ] Railway API keys (30 environment variables)
- [ ] Vercel environment variables
- [ ] SSL certificates (for local HTTPS)
- [ ] Database connection strings (Supabase)
- [ ] Redis connection string (Upstash)

---

## 🗺️ Implementation Roadmap

### **Milestone 1: Windows Environment Setup** ⏱️ 30 minutes ✅ COMPLETE

#### Objectives:
- ✅ Install Docker Desktop on Windows
- ✅ Clone repository to Windows machine
- ✅ Verify Docker is working

#### Tasks:

**1.1 Install Docker Desktop**
- ✅ Download Docker Desktop from https://www.docker.com/products/docker-desktop
- ✅ Install with WSL 2 backend (recommended)
- ✅ Start Docker Desktop
- ✅ Verify installation: `docker --version` (v28.5.1)
- ✅ Verify Docker Compose: `docker-compose --version` (v2.40.0)

**1.2 Clone Repository**
```powershell
# On Windows machine - COMPLETED
cd D:\User\Projects
git clone https://github.com/kaisersoser/bloggen-web-service.git
cd bloggen-web-service
```

**1.3 Verify Docker Network**
- ✅ Ensure Docker Desktop is running
- ✅ Test Docker with: `docker run hello-world` (PASSED)
- ✅ Confirm WSL 2 integration (if using WSL)

**Success Criteria:**
- ✅ Docker Desktop running without errors
- ✅ Repository cloned on Windows at D:\User\Projects\bloggen-web-service
- ✅ Docker hello-world test passes

---

### **Milestone 2: Docker Configuration for Staging** ⏱️ 45 minutes ✅ COMPLETE

#### Objectives:
- ✅ Create Windows-specific Docker configuration
- ✅ Set up environment variables for staging
- ✅ Configure networking and ports

#### Tasks:

**2.1 Create Staging Docker Compose File** ✅

Created `docker-compose.staging.yml`:
- Backend service: Maps port 5000:8080 (matches Railway's internal port)
- Frontend service: Maps port 3000:3000
- Network: bloggen-staging-network (isolated bridge network)
- Health checks: Backend health endpoint monitoring
- Service dependencies: Frontend depends on backend health

**2.2 Create Staging Environment Files** ✅

Created environment configuration files:
- ✅ `backend/.env.staging.example` - Template with placeholders
- ✅ `frontend-nextjs/blog-generator-ui/.env.staging.example` - Template with placeholders
- ✅ User-specific `.env.staging` files ignored by git (must be configured locally)

Configuration includes:
- Database URLs (Supabase or local PostgreSQL)
- Redis configuration (Upstash or local Redis)
- API keys (OpenAI, Replicate, Unsplash)
- OAuth credentials (Google, GitHub, Microsoft)
- Environment-specific settings (staging mode, debug logging)

**2.3 Create PowerShell Control Scripts** ✅

Created Windows automation scripts:
- ✅ `scripts/staging-start.ps1` - Start staging environment with health checks
- ✅ `scripts/staging-stop.ps1` - Stop containers gracefully
- ✅ `scripts/staging-test.ps1` - Run automated health checks and validation
- ✅ `scripts/staging-clean.ps1` - Clean Docker resources (interactive confirmation)

**2.4 Create Documentation** ✅

Created comprehensive setup guide:
- ✅ `docs/STAGING_SETUP_GUIDE.md` - Complete Windows staging guide
  - Configuration instructions
  - Running staging environment
  - Testing workflow
  - Troubleshooting section
  - Development workflow
  - Quick reference table

**Success Criteria:**
- ✅ docker-compose.staging.yml created and configured
- ✅ Environment templates created (.env.staging.example files)
- ✅ PowerShell control scripts created (4 scripts)
- ✅ Staging setup documentation complete
- ✅ All files committed to feature/staging-environment branch

Create `docker-compose.staging.yml`:

```yaml
version: '3.8'

services:
  backend-staging:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: bloggen-backend-staging
    ports:
      - "5000:8080"  # Map to Railway's internal port
    environment:
      - PORT=8080
      - NODE_ENV=staging
      - RAILWAY_ENVIRONMENT=staging
    env_file:
      - ./backend/.env.staging
    networks:
      - bloggen-staging-network
    restart: unless-stopped

  frontend-staging:
    build:
      context: ./frontend-nextjs/blog-generator-ui
      dockerfile: Dockerfile
    container_name: bloggen-frontend-staging
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=staging
      - NEXT_PUBLIC_API_URL=http://localhost:5000
    env_file:
      - ./frontend-nextjs/blog-generator-ui/.env.staging
    depends_on:
      - backend-staging
    networks:
      - bloggen-staging-network
    restart: unless-stopped

networks:
  bloggen-staging-network:
    driver: bridge
```

**2.2 Create Staging Environment Files**

Create `backend/.env.staging`:
```bash
# Copy from backend/.env.local and modify for staging
PORT=8080
ENVIRONMENT=staging

# Database (use Supabase production)
DATABASE_URL=postgresql://...

# Redis (use Upstash production)
REDIS_URL=rediss://...

# AI Services (use production keys with limits)
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# Authentication (staging-specific)
NEXTAUTH_SECRET=<generate-new-secret>
NEXTAUTH_URL=http://localhost:3000

# All other 30 environment variables...
```

Create `frontend-nextjs/blog-generator-ui/.env.staging`:
```bash
# NextAuth Configuration
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=<same-as-backend>

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:5000
API_BASE_URL=http://backend-staging:8080

# Database
DATABASE_URL=<same-as-production>

# OAuth (create staging OAuth apps or use production)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_ID=...
GITHUB_SECRET=...

# All other environment variables...
```

**2.3 Create Dockerfiles (if not existing)**

`backend/Dockerfile` (already exists - verify it works for staging)

`frontend-nextjs/blog-generator-ui/Dockerfile` (create if needed):
```dockerfile
FROM node:18-alpine AS base

# Install dependencies
FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Build application
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Production image
FROM base AS runner
WORKDIR /app
ENV NODE_ENV=staging
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000

CMD ["node", "server.js"]
```

**2.4 Create Staging Control Scripts**

Create `scripts/staging-start.ps1` (PowerShell):
```powershell
# Start staging environment on Windows
Write-Host "🚀 Starting BlogGen Staging Environment..." -ForegroundColor Green

# Check if Docker is running
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Pull latest changes
Write-Host "📥 Pulling latest changes from main branch..." -ForegroundColor Cyan
git checkout main
git pull origin main

# Build and start containers
Write-Host "🔨 Building and starting containers..." -ForegroundColor Cyan
docker-compose -f docker-compose.staging.yml up --build -d

# Wait for services to be healthy
Write-Host "⏳ Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check service status
docker-compose -f docker-compose.staging.yml ps

# Show logs
Write-Host "`n📋 Service logs (Ctrl+C to exit):" -ForegroundColor Cyan
docker-compose -f docker-compose.staging.yml logs -f
```

Create `scripts/staging-stop.ps1`:
```powershell
# Stop staging environment
Write-Host "🛑 Stopping BlogGen Staging Environment..." -ForegroundColor Yellow
docker-compose -f docker-compose.staging.yml down

Write-Host "✅ Staging environment stopped" -ForegroundColor Green
```

Create `scripts/staging-clean.ps1`:
```powershell
# Clean staging environment (remove containers, volumes, images)
Write-Host "🧹 Cleaning staging environment..." -ForegroundColor Yellow

docker-compose -f docker-compose.staging.yml down -v --rmi all

Write-Host "✅ Staging environment cleaned" -ForegroundColor Green
```

Create `scripts/staging-test.ps1`:
```powershell
# Test staging environment
Write-Host "🧪 Testing Staging Environment..." -ForegroundColor Cyan

# Test backend health
Write-Host "`nTesting backend health endpoint..." -ForegroundColor Yellow
$backendHealth = Invoke-RestMethod -Uri "http://localhost:5000/health" -Method Get -ErrorAction SilentlyContinue

if ($backendHealth.status -eq "healthy") {
    Write-Host "✅ Backend is healthy" -ForegroundColor Green
} else {
    Write-Host "❌ Backend health check failed" -ForegroundColor Red
}

# Test frontend
Write-Host "`nTesting frontend..." -ForegroundColor Yellow
$frontendResponse = Invoke-WebRequest -Uri "http://localhost:3000" -Method Get -ErrorAction SilentlyContinue

if ($frontendResponse.StatusCode -eq 200) {
    Write-Host "✅ Frontend is accessible" -ForegroundColor Green
} else {
    Write-Host "❌ Frontend is not accessible" -ForegroundColor Red
}

Write-Host "`n📊 Service URLs:" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "  Backend:  http://localhost:5000" -ForegroundColor White
Write-Host "  Backend Health: http://localhost:5000/health" -ForegroundColor White
Write-Host "  Backend Docs: http://localhost:5000/docs" -ForegroundColor White
```

**Success Criteria:**
- ✅ `docker-compose.staging.yml` created and validated
- ✅ `.env.staging` files created with all required variables
- ✅ PowerShell control scripts created and executable
- ✅ Dockerfiles verified or created

---

### **Milestone 3: Git Workflow & Branch Strategy** ⏱️ 20 minutes

#### Objectives:
- Define branch strategy
- Create branch protection rules
- Document git workflow

#### Tasks:

**3.1 Branch Strategy**

```
main (protected)
  ↓
  Automatic deploy to Production (Railway + Vercel)

feature/* (short-lived)
  ↓
  Merge to main after staging tests pass
```

**Simple two-branch model:**
- `main` = production-ready code
- `feature/*` = development branches (created as needed)

**3.2 Git Workflow Commands**

Create `.github/workflows/documentation/GIT_WORKFLOW.md`:

```markdown
# Git Workflow for BlogGen Development

## Daily Development Flow

### 1. Start New Feature
```bash
# On Linux dev server
cd /path/to/bloggen-web-service
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

### 2. Develop and Test Locally
```bash
# Make changes on Linux dev server
git add .
git commit -m "feat: description of changes"

# Can create multiple commits
git commit -m "fix: bug fix"
git commit -m "docs: update documentation"
```

### 3. Test on Windows Staging
```bash
# On Linux dev server - push feature branch
git push origin feature/your-feature-name

# On Windows machine - pull and test
cd C:\Projects\bloggen-web-service
git fetch origin
git checkout feature/your-feature-name
git pull origin feature/your-feature-name

# Start staging environment
.\scripts\staging-start.ps1

# Run tests
.\scripts\staging-test.ps1

# Manual testing in browser
# - http://localhost:3000 (frontend)
# - http://localhost:5000/health (backend health)
# - Test blog generation end-to-end
```

### 4. Deploy to Production
```bash
# If staging tests pass, merge to main
git checkout main
git pull origin main
git merge feature/your-feature-name
git push origin main

# Vercel and Railway auto-deploy from main branch
# Monitor deployments in dashboards
```

### 5. Cleanup
```bash
# On Windows - stop staging
.\scripts\staging-stop.ps1

# Delete feature branch (optional)
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

## Emergency Hotfix Flow

```bash
# Create hotfix directly from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug-fix

# Make fix
git commit -m "hotfix: critical bug description"

# Test in staging (same as above)

# Merge and deploy immediately
git checkout main
git merge hotfix/critical-bug-fix
git push origin main
```

## Rollback Procedure

```bash
# If production deployment breaks:

# Option 1: Revert last commit
git revert HEAD
git push origin main

# Option 2: Revert to specific commit
git revert <commit-hash>
git push origin main

# Option 3: Force rollback (use with caution)
git reset --hard <previous-good-commit>
git push origin main --force
```
```

**3.3 Commit Message Convention**

Use conventional commits:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting)
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Maintenance tasks

**Success Criteria:**
- ✅ Branch strategy documented
- ✅ Git workflow guide created
- ✅ Commit conventions defined
- ✅ Rollback procedure documented

---

### **Milestone 4: Testing & Validation Procedures** ⏱️ 30 minutes

#### Objectives:
- Create staging test checklist
- Define production validation steps
- Document common issues and fixes

#### Tasks:

**4.1 Create Staging Test Checklist**

Create `docs/STAGING_TEST_CHECKLIST.md`:

```markdown
# Staging Environment Test Checklist

## Pre-Deployment Checks

### Environment Setup
- [ ] Docker Desktop is running
- [ ] Latest code pulled from feature branch
- [ ] `.env.staging` files are up to date
- [ ] No uncommitted changes in staging branch

### Service Startup
- [ ] Run `.\scripts\staging-start.ps1`
- [ ] All containers start without errors
- [ ] No error messages in logs
- [ ] Backend logs show: "✅ FastAPI application startup complete"
- [ ] Frontend logs show successful build

## Backend Tests

### Health Checks
- [ ] `http://localhost:5000/health` returns 200 OK
- [ ] All services show `healthy: true`
- [ ] Database connection successful
- [ ] Redis connection successful

### API Endpoints
- [ ] GET `/health` - Health check
- [ ] GET `/docs` - API documentation loads
- [ ] POST `/generate-blog` - Requires authentication (403 expected)

### Authentication
- [ ] Can access JWT token endpoint
- [ ] Token validation works

## Frontend Tests

### Page Loading
- [ ] `http://localhost:3000` loads homepage
- [ ] No console errors on homepage
- [ ] UI renders correctly

### Authentication Flow
- [ ] Can navigate to login page
- [ ] Google OAuth redirects correctly
- [ ] GitHub OAuth redirects correctly
- [ ] After login, redirects to dashboard
- [ ] User profile displays correctly

### Blog Generation (Critical Path)
- [ ] Can access blog generation page
- [ ] Topic input field works
- [ ] Instructions field works
- [ ] "Generate Blog" button enabled
- [ ] Click generates blog successfully
- [ ] Real-time console shows progress
- [ ] SSE connection establishes
- [ ] All phases complete:
  - [ ] Research phase
  - [ ] Content generation phase
  - [ ] Fact checking phase
  - [ ] Finalization phase
- [ ] Final blog displays correctly
- [ ] Images load properly
- [ ] Markdown renders correctly
- [ ] Can copy blog content
- [ ] Can download blog

### Previous Blogs
- [ ] Can view list of previous blogs
- [ ] Can open blog details
- [ ] Can delete blogs

### User Stats
- [ ] Generation count shows correctly
- [ ] Generation limit displays
- [ ] Role badge displays (FREE/PREMIUM/ADMIN)

## Performance Tests

- [ ] Blog generation completes in < 5 minutes
- [ ] No memory leaks in browser console
- [ ] Docker containers stay under resource limits
- [ ] SSE connection remains stable

## Error Handling

- [ ] Test with invalid input (empty topic)
- [ ] Test with exceeding generation limit
- [ ] Test with network disconnection
- [ ] Error messages are user-friendly

## Browser Compatibility

- [ ] Test in Chrome
- [ ] Test in Firefox (optional)
- [ ] Test in Edge (optional)

## Final Checks

- [ ] No 500 errors in browser console
- [ ] No error logs in Docker containers
- [ ] All tests passed
- [ ] Ready for production deployment

## Staging Shutdown

- [ ] Run `.\scripts\staging-stop.ps1`
- [ ] Containers stop cleanly
- [ ] No orphaned processes
```

**4.2 Create Production Validation Checklist**

Create `docs/PRODUCTION_VALIDATION.md`:

```markdown
# Production Deployment Validation

## Post-Deployment Checks (Run Immediately After Deploy)

### Deployment Status
- [ ] Vercel deployment shows "Success"
- [ ] Railway deployment shows "Active"
- [ ] No build errors in either platform

### Service Health
- [ ] `https://bloggen-web-service-production.up.railway.app/health` returns healthy
- [ ] `https://bloggen-web-service.vercel.app` loads homepage
- [ ] No 502/503 errors

### Smoke Tests
- [ ] Can log in with Google OAuth
- [ ] Can generate a simple blog (test topic)
- [ ] SSE streaming works
- [ ] Blog saves correctly
- [ ] Can view blog details

### Monitor for 15 minutes
- [ ] Check Railway logs for errors
- [ ] Check Vercel logs for errors
- [ ] Monitor error tracking (if configured)
- [ ] Check for unexpected API costs

## If Issues Detected

### Immediate Actions
1. Check if issue is critical (prevents blog generation)
2. If critical: Run rollback procedure
3. If non-critical: Create hotfix branch

### Rollback Decision Tree
- **Critical bugs**: Rollback immediately
- **Performance issues**: Monitor for 1 hour
- **Minor UI bugs**: Create hotfix for next deployment
- **500 errors in console (non-blocking)**: Defer to next release

## Communication

- [ ] Update team/stakeholders on deployment status
- [ ] Document any issues encountered
- [ ] Update changelog with deployment notes
```

**4.3 Create Troubleshooting Guide**

Create `docs/STAGING_TROUBLESHOOTING.md`:

```markdown
# Staging Environment Troubleshooting

## Common Issues and Solutions

### Docker Desktop Not Starting
**Symptoms**: `docker info` fails, containers won't start

**Solutions**:
1. Restart Docker Desktop
2. Check WSL 2 is enabled (Windows Features)
3. Ensure Hyper-V is enabled
4. Restart computer

### Port Already in Use
**Error**: `Port 5000 is already allocated`

**Solutions**:
```powershell
# Find process using port
netstat -ano | findstr :5000

# Kill process (replace <PID> with actual PID)
taskkill /PID <PID> /F

# Or change port in docker-compose.staging.yml
```

### Container Fails to Start
**Symptoms**: Container exits immediately

**Solutions**:
```powershell
# Check logs
docker logs bloggen-backend-staging
docker logs bloggen-frontend-staging

# Common fixes:
# 1. Missing environment variables
# 2. Invalid database connection
# 3. Port conflicts
# 4. Build errors
```

### Backend 502 Errors
**Symptoms**: Frontend can't reach backend

**Solutions**:
1. Check backend is running: `docker ps`
2. Check backend logs: `docker logs bloggen-backend-staging`
3. Verify network: `docker network ls`
4. Test health endpoint directly: `curl http://localhost:5000/health`

### Frontend Build Fails
**Symptoms**: Docker build fails during npm install or build

**Solutions**:
```powershell
# Clear npm cache
docker-compose -f docker-compose.staging.yml down
docker volume prune -f
docker-compose -f docker-compose.staging.yml build --no-cache frontend-staging
```

### Database Connection Fails
**Symptoms**: Backend shows database connection errors

**Solutions**:
1. Verify `DATABASE_URL` in `.env.staging`
2. Check Supabase status
3. Verify IP whitelist (if applicable)
4. Test connection from Windows:
```powershell
# Install psql or use online tool
psql $DATABASE_URL -c "SELECT 1"
```

### Redis Connection Fails
**Symptoms**: Backend shows Redis errors

**Solutions**:
1. Verify `REDIS_URL` in `.env.staging`
2. Check Upstash status
3. Verify TLS/SSL settings (rediss:// vs redis://)

### OAuth Not Working
**Symptoms**: Login redirects fail

**Solutions**:
1. Verify `NEXTAUTH_URL=http://localhost:3000`
2. Check Google/GitHub OAuth app has `http://localhost:3000/api/auth/callback/google` in redirect URLs
3. Verify `NEXTAUTH_SECRET` matches in both frontend and backend
4. Check OAuth credentials are correct

### Memory Issues
**Symptoms**: Containers crash or restart

**Solutions**:
```powershell
# Increase Docker memory limit (Docker Desktop Settings)
# Recommended: 8GB RAM, 4GB swap

# Check resource usage
docker stats
```

### Disk Space Issues
**Symptoms**: Build fails with "no space left"

**Solutions**:
```powershell
# Clean up Docker resources
docker system prune -a --volumes

# Remove old images
docker image prune -a

# Check disk space
docker system df
```

## Debug Commands

```powershell
# View all containers
docker ps -a

# View container logs (live)
docker logs -f bloggen-backend-staging

# Enter container shell
docker exec -it bloggen-backend-staging sh

# Inspect container
docker inspect bloggen-backend-staging

# View network details
docker network inspect bloggen-staging-network

# Restart specific service
docker-compose -f docker-compose.staging.yml restart backend-staging

# Rebuild specific service
docker-compose -f docker-compose.staging.yml up -d --build backend-staging
```

## Getting Help

1. Check this guide first
2. Review Docker logs
3. Check GitHub issues
4. Contact development team
```

**Success Criteria:**
- ✅ Staging test checklist created
- ✅ Production validation checklist created
- ✅ Troubleshooting guide created
- ✅ All checklists are actionable and clear

---

### **Milestone 5: Documentation & Training** ⏱️ 15 minutes

#### Objectives:
- Create quick-start guide
- Document pipeline overview
- Create visual workflow diagram

#### Tasks:

**5.1 Create Quick Start Guide**

Create `docs/QUICK_START_STAGING.md`:

```markdown
# Quick Start: Windows Staging Environment

## First Time Setup (Do Once)

### 1. Install Docker Desktop
- Download from https://www.docker.com/products/docker-desktop
- Install with WSL 2 backend
- Restart computer if prompted

### 2. Clone Repository
```powershell
cd C:\Projects
git clone https://github.com/kaisersoser/bloggen-web-service.git
cd bloggen-web-service
```

### 3. Copy Environment Files
```powershell
# Copy backend environment
copy backend\.env.example backend\.env.staging
# Edit backend\.env.staging with your values

# Copy frontend environment
copy frontend-nextjs\blog-generator-ui\.env.example frontend-nextjs\blog-generator-ui\.env.staging
# Edit frontend-nextjs\blog-generator-ui\.env.staging with your values
```

## Daily Usage

### Start Staging Environment
```powershell
cd C:\Projects\bloggen-web-service
.\scripts\staging-start.ps1
```

Wait ~30 seconds for services to start.

### Access Services
- Frontend: http://localhost:3000
- Backend: http://localhost:5000
- Backend Health: http://localhost:5000/health
- API Docs: http://localhost:5000/docs

### Run Tests
```powershell
.\scripts\staging-test.ps1
```

### View Logs
```powershell
docker-compose -f docker-compose.staging.yml logs -f
```

### Stop Staging Environment
```powershell
.\scripts\staging-stop.ps1
```

## Troubleshooting

If something doesn't work:
1. Check Docker Desktop is running
2. Run `.\scripts\staging-clean.ps1` to reset
3. Run `.\scripts\staging-start.ps1` again
4. Check `docs/STAGING_TROUBLESHOOTING.md` for specific errors

## Tips

- Always pull latest code before testing: `git pull origin main`
- Stop staging when not in use to save resources
- Use `staging-clean.ps1` weekly to clear old images
```

**5.2 Create Pipeline Overview Diagram**

Create `docs/PIPELINE_OVERVIEW.md` with ASCII art diagram:

```markdown
# Development Pipeline Overview

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Development Workflow                     │
└─────────────────────────────────────────────────────────────┘

┌──────────────────┐
│ Linux Dev Server │  ← Primary development
│   (VSCode SSH)   │  ← Code editing, git commits
└────────┬─────────┘
         │
         │ git push feature/branch
         │
         ▼
┌────────────────────┐
│  GitHub Repository │
│   (main branch)    │
└────────┬───────────┘
         │
         │ git checkout feature/branch
         │
         ▼
┌─────────────────────┐
│  Windows Machine    │  ← Staging environment
│  (Docker Desktop)   │  ← Testing before production
└────────┬────────────┘
         │
         │ docker-compose up
         │
         ▼
┌──────────────────────────────────────────────────────┐
│            Docker Staging Environment                │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────────┐      ┌──────────────────┐     │
│  │ Backend Container│ ←──→ │Frontend Container│     │
│  │  (FastAPI/Python)│      │   (Next.js)      │     │
│  │  Port 5000       │      │   Port 3000      │     │
│  └────────┬─────────┘      └────────┬─────────┘     │
│           │                         │               │
│           └─────────┬───────────────┘               │
│                     │                               │
│                     ▼                               │
│          ┌──────────────────────┐                  │
│          │  External Services   │                  │
│          │  - Supabase (DB)     │                  │
│          │  - Upstash (Redis)   │                  │
│          │  - OpenAI            │                  │
│          └──────────────────────┘                  │
└──────────────────────────────────────────────────────┘
         │
         │ Tests pass ✓
         │ Manual validation ✓
         │
         │ git merge to main
         │ git push origin main
         │
         ▼
┌──────────────────────────────────────────────────────┐
│              Production Environment                  │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────────┐        ┌──────────────────┐   │
│  │  Railway         │  ←───→ │     Vercel       │   │
│  │  (Backend)       │        │   (Frontend)     │   │
│  │  Auto-deploy     │        │   Auto-deploy    │   │
│  └──────────────────┘        └──────────────────┘   │
│                                                      │
│  URL: bloggen-web-service-production.up.railway.app │
│  URL: bloggen-web-service.vercel.app                │
└──────────────────────────────────────────────────────┘
```

## Workflow Steps

### Development Phase
1. Develop on Linux server via VSCode Remote SSH
2. Commit changes to feature branch
3. Push to GitHub

### Staging Phase  
4. Pull feature branch on Windows
5. Start Docker staging environment
6. Run automated tests
7. Perform manual testing
8. Verify all features work

### Production Phase
9. Merge feature branch to main
10. Push to GitHub
11. Vercel auto-deploys frontend
12. Railway auto-deploys backend
13. Validate production deployment
14. Monitor for issues

## Rollback Flow

```
Production Issue Detected
         │
         ▼
    [Critical?]
         │
    ┌────┴────┐
    │         │
   Yes       No
    │         │
    │         └──→ Create Hotfix Branch
    │              Test in Staging
    │              Deploy When Ready
    │
    ▼
git revert HEAD
git push origin main
    │
    ▼
Auto-redeploy Previous Version
    │
    ▼
Validate Production
    │
    ▼
Create Hotfix Branch
```

## Key Principles

1. **Never push directly to main** without staging tests
2. **Always test in staging** before production deploy
3. **Keep staging environment clean** (rebuild weekly)
4. **Monitor production** for 15 minutes after deployment
5. **Document issues** encountered during testing
```

**Success Criteria:**
- ✅ Quick start guide created
- ✅ Pipeline overview documented with diagrams
- ✅ Workflow is clear and actionable

---

## 📊 Implementation Timeline

| Milestone | Duration | Dependencies | Risk Level | Status |
|-----------|----------|--------------|------------|--------|
| 1. Windows Setup | 30 min | None | Low | ✅ **COMPLETE** |
| 2. Docker Config | 45 min | Milestone 1 | Medium | 🔄 **IN PROGRESS** |
| 3. Git Workflow | 20 min | None | Low | ⏳ Pending |
| 4. Testing Procedures | 30 min | Milestone 2 | Low | ⏳ Pending |
| 5. Documentation | 15 min | All above | Low | ⏳ Pending |

**Total Estimated Time**: 2 hours 20 minutes  
**Time Spent**: 30 minutes  
**Remaining**: 1 hour 50 minutes

---

## 🎯 Success Metrics

### Immediate (After Implementation)
- [ ] Can start staging environment with one command
- [ ] Can run full test suite in staging
- [ ] Can deploy to production with confidence
- [ ] Zero manual environment configuration

### Long-term (After 1 Month)
- [ ] Reduced production bugs by 50%
- [ ] Faster feature deployment (same day)
- [ ] Improved confidence in deployments
- [ ] Better documentation for new developers

---

## 🚨 Risks & Mitigation

### Risk 1: Docker Desktop Licensing
**Risk**: Docker Desktop requires paid license for commercial use in enterprises
**Mitigation**: Confirm your usage scenario, consider alternatives (Podman) if needed
**Impact**: Medium

### Risk 2: Windows Performance
**Risk**: Docker on Windows may be slower than Linux
**Mitigation**: Allocate sufficient RAM (8GB+), use WSL 2 backend
**Impact**: Low

### Risk 3: Environment Drift
**Risk**: Staging differs from production over time
**Mitigation**: Regular rebuilds, use same environment variables as production
**Impact**: Medium

### Risk 4: Database State
**Risk**: Testing in staging uses production database
**Mitigation**: Clearly mark staging-generated content, or use separate staging DB
**Impact**: Low (manageable)

### Risk 5: Cost of Testing
**Risk**: API calls in staging consume production quotas
**Mitigation**: Use lower rate limits, implement cost tracking
**Impact**: Low

---

## 📝 Next Steps

### Before Implementation
- [ ] Review this plan with stakeholders
- [ ] Approve Milestone order and timeline
- [ ] Gather all required credentials
- [ ] Schedule implementation time

### During Implementation
- [ ] Execute Milestones in order
- [ ] Test each Milestone before proceeding
- [ ] Document any deviations from plan
- [ ] Take notes on improvements needed

### After Implementation
- [ ] Run full staging test suite
- [ ] Deploy one test feature through new pipeline
- [ ] Gather feedback
- [ ] Update documentation based on learnings
- [ ] Train any additional team members

---

## 📞 Support

**Questions or Issues During Implementation?**
- Refer to milestone-specific success criteria
- Check troubleshooting guide
- Review Docker Desktop documentation
- Reach out to development team

---

## 📄 Appendix

### A. Required Environment Variables (30 total)

#### Backend `.env.staging`
```
PORT=8080
ENVIRONMENT=staging
DATABASE_URL=<supabase-url>
REDIS_URL=<upstash-url>
OPENAI_API_KEY=<key>
GOOGLE_API_KEY=<key>
NEXTAUTH_SECRET=<secret>
NEXTAUTH_URL=http://localhost:3000
# ... 22 more variables
```

#### Frontend `.env.staging`
```
NEXTAUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:5000
DATABASE_URL=<supabase-url>
GOOGLE_CLIENT_ID=<id>
GOOGLE_CLIENT_SECRET=<secret>
GITHUB_ID=<id>
GITHUB_SECRET=<secret>
# ... more variables
```

### B. PowerShell Execution Policy

If PowerShell scripts don't run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### C. Useful Docker Commands

```powershell
# View all resources
docker ps -a
docker images
docker volume ls
docker network ls

# Clean everything
docker system prune -a --volumes

# View resource usage
docker stats

# Export container logs
docker logs bloggen-backend-staging > backend.log
```

---

**Document End**

Review this plan, provide feedback, and approve to proceed with implementation.
