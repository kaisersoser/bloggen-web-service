# 🚀 Step-by-Step Production Deployment Guide

**Last Updated:** October 15, 2025  
**Deployment Strategy:** Full Serverless (Vercel + Railway + Upstash)  
**Estimated Time:** 2-4 hours (first deployment)

---

## 📋 Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Phase 1: Infrastructure Setup](#phase-1-infrastructure-setup)
3. [Phase 2: Database Setup](#phase-2-database-setup) ← Updated: Choose your path
4. [Phase 3: Backend Deployment](#phase-3-backend-deployment)
5. [Phase 4: Frontend Deployment](#phase-4-frontend-deployment)
6. [Phase 5: Verification & Testing](#phase-5-verification--testing)
7. [Phase 6: Monitoring Setup](#phase-6-monitoring-setup)
8. [Automated Deployment Scripts](#automated-deployment-scripts)
9. [Troubleshooting](#troubleshooting)

---

## 📖 Additional Guides

- **[Railway Configuration Guide](./RAILWAY_CONFIGURATION.md)** - Detailed Railway setup walkthrough
- **[Environment Configuration](./ENVIRONMENT_CONFIGURATION.md)** - Local vs Production setup
- **[Quick Reference](./DEPLOYMENT_QUICK_REFERENCE.md)** - Fast deployment commands

---

## ✅ Pre-Deployment Checklist

### 1. Required Accounts (Sign up before starting)

- [ ] **GitHub Account** (you have this)
- [ ] **Supabase Account** - https://supabase.com/ (PostgreSQL) ← May already have
- [ ] **Upstash Account** - https://console.upstash.com/ (Redis) ← NEW
- [ ] **Railway Account** - https://railway.app/ (Backend hosting) ← NEW
- [ ] **Vercel Account** - https://vercel.com/ (Frontend hosting)
- [ ] **Domain Name** (optional, can use free subdomains)

### 2. Required Tools

```bash
# Check if you have these installed
git --version        # Should be 2.x+
node --version       # Should be 18.x+ or 20.x+
npm --version        # Should be 9.x+ or 10.x+
python --version     # Should be 3.11+

# Install CLI tools (optional, makes deployment easier)
npm install -g vercel      # Vercel CLI
npm install -g @railway/cli  # Railway CLI
```

### 3. Environment Secrets to Prepare

```bash
# Generate strong secrets now (save these securely)
openssl rand -base64 32  # For JWT_SECRET
openssl rand -base64 32  # For NEXTAUTH_SECRET

# API Keys you already have:
# - OPENAI_API_KEY
# - UNSPLASH_ACCESS_KEY
# - AWS credentials (if using S3)
# - OAuth credentials (Google, GitHub)
```

### 4. Code Preparation

```bash
# 1. Ensure you're on the main branch
git checkout main
git pull origin main

# 2. Ensure all tests pass locally
cd backend
source .venv/bin/activate
pytest src/tests/

cd ../frontend-nextjs/blog-generator-ui
npm test

# 3. Ensure local app works
# Backend: https://localhost:5000/health
# Frontend: https://localhost:3000

# 4. Commit any pending changes
git status
git add .
git commit -m "Prepare for production deployment"
git push origin main
```

---

## 🏗️ Phase 1: Infrastructure Setup

**Estimated Time:** 30-45 minutes

### Step 1.1: Supabase Setup (PostgreSQL) - 10 minutes

**Already done if you're using Supabase. Skip to Step 1.2 if configured.**

```bash
# 1. Sign up at https://supabase.com/

# 2. Create new project
#    - Organization: Your name
#    - Project name: bloggen-production
#    - Database password: [SAVE THIS SECURELY]
#    - Region: Choose closest to your users (e.g., us-east-1)
#    - Pricing: Free tier (upgrade later if needed)

# 3. Wait 2-3 minutes for provisioning

# 4. Get connection details
#    Dashboard → Settings → Database → Connection string
#    
#    Copy these values:
#    DATABASE_URL: postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
#    SUPABASE_URL: https://[PROJECT].supabase.co
#    SUPABASE_KEY: [anon_key from API settings]

# 5. Test connection
psql "postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres" -c "SELECT version();"

# ✅ If you see PostgreSQL version, success!
```

**Save these for later:**
```bash
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
SUPABASE_URL=https://[PROJECT].supabase.co
SUPABASE_KEY=[your_anon_key]
```

---

### Step 1.2: Upstash Redis Setup - 10 minutes

```bash
# 1. Sign up at https://console.upstash.com/
#    - Sign in with GitHub (easiest)

# 2. Create Redis database
#    - Click "Create Database"
#    - Name: bloggen-prod-redis
#    - Type: Regional (cheaper, sufficient for MVP)
#    - Region: us-east-1 (or same as your Supabase)
#    - TLS: Enabled (default)
#    - Eviction: No eviction (recommended for your use case)

# 3. Wait ~30 seconds for provisioning

# 4. Get connection details
#    Dashboard → Your Database → Details
#    
#    Copy these values (you'll see 2 options):

#    Option A: Redis Protocol (use this first)
REDIS_URL=redis://default:[PASSWORD]@[REGION].upstash.io:6379

#    Option B: REST API (alternative, good for serverless)
UPSTASH_REDIS_REST_URL=https://[YOUR-DB].upstash.io
UPSTASH_REDIS_REST_TOKEN=[your_token]

# 5. Test connection
redis-cli -u "redis://default:[PASSWORD]@[REGION].upstash.io:6379" PING

# ✅ If you see "PONG", success!
```

**Save these for later:**
```bash
REDIS_URL=redis://default:[PASSWORD]@[REGION].upstash.io:6379
UPSTASH_REDIS_REST_URL=https://[YOUR-DB].upstash.io
UPSTASH_REDIS_REST_TOKEN=[your_token]
```

---

### Step 1.3: Railway Setup (Backend Hosting) - 10 minutes

```bash
# 1. Sign up at https://railway.app/
#    - Sign in with GitHub (easiest)

# 2. Create new project
#    - Click "New Project"
#    - Select "Deploy from GitHub repo"
#    - Authorize Railway to access your GitHub
#    - Select repository: bloggen-web-service
#    - Railway will detect it's a Python project

# 3. Configure backend service
#    - Root Directory: backend/
#    - Start Command: python src/main.py
#    - Health Check: /health

# 4. Don't deploy yet! We need to add environment variables first.

# 5. Get Railway domain
#    - After creating service, Railway assigns a URL like:
#      https://your-app.up.railway.app
#    - You can add custom domain later

# ✅ Railway project created! Moving to environment variables next.
```

---

### Step 1.4: Vercel Setup (Frontend Hosting) - 10 minutes

```bash
# 1. Sign up at https://vercel.com/
#    - Sign in with GitHub (easiest)

# 2. Import project
#    - Click "New Project"
#    - Import Git Repository
#    - Select: bloggen-web-service
#    - Framework Preset: Next.js (auto-detected)
#    - Root Directory: frontend-nextjs/blog-generator-ui
#    - Build Command: npm run build (default)
#    - Output Directory: .next (default)

# 3. Don't deploy yet! We need to add environment variables first.

# 4. Get Vercel domain
#    - Vercel assigns a URL like:
#      https://bloggen-web-service.vercel.app
#    - You can add custom domain later

# ✅ Vercel project created! Moving to environment variables next.
```

---

## 🗄️ Phase 2: Database Setup

**Estimated Time:** 5-20 minutes (depending on your situation)

> **Choose Your Path:**
> - **Option A:** Using Existing Supabase Database (5 minutes) ← **Most users**
> - **Option B:** New Supabase Database Setup (20 minutes)

---

### Option A: Using Existing Supabase Database ✅

**Use this if:** You already have a working Supabase database with all tables, RLS policies, and data.

#### Step 2A.1: Verify Existing Database

```bash
# 1. Get your Supabase connection string
# Go to Supabase Dashboard → Settings → Database → Connection String → URI

# Your DATABASE_URL should look like:
# postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres

# 2. Verify all required tables exist
# Go to Supabase Dashboard → Table Editor
# Confirm these tables are present:
# ✓ User
# ✓ Account  
# ✓ Session
# ✓ VerificationToken
# ✓ Blog (or blogs)
# ✓ audit_sessions (if using audit features)
# ✓ llm_api_calls (if using audit features)

# 3. (Optional) Test connection locally
cd /home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/frontend-nextjs/blog-generator-ui
export DATABASE_URL="your-supabase-connection-string"
npx prisma db pull
# Should show: "Introspected X models from the database"

# ✅ Database verified! Skip to Phase 3: Backend Deployment
```

#### Step 2A.2: Save Connection Strings

```bash
# Copy these from Supabase Dashboard → Settings → Database:

# 1. Connection String (for Railway backend & Vercel frontend)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres

# 2. Direct Connection String (for Prisma migrations if needed)
DIRECT_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres

# 3. Supabase Project URL & Keys (from Settings → API)
SUPABASE_URL=https://[PROJECT].supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-key (keep secret!)

# Save these securely - you'll use them in Phase 3 & 4

# ✅ Connection strings ready! Proceed to Phase 3.
```

---

### Option B: New Supabase Database Setup ⚙️

**Use this if:** You're starting fresh or need to set up a brand new Supabase project.

#### Step 2B.1: Run Prisma Migrations

```bash
# 1. Navigate to frontend directory
cd /home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/frontend-nextjs/blog-generator-ui

# 2. Set production database URL temporarily
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres"

# 3. Run migrations
npx prisma migrate deploy

# Expected output:
# ✔ Prisma Migrate applied the following migration(s):
# migrations/
#   └─ 20231115000000_init/
#       └─ migration.sql

# 4. Verify schema
npx prisma db pull

# 5. Generate Prisma client
npx prisma generate

# 6. (Optional) Open Prisma Studio to verify tables
npx prisma studio
# Opens at http://localhost:5555
# Check that tables exist: User, Session, Account, Blog, etc.

# ✅ Database schema deployed!
```

#### Step 2B.2: Verify Database Structure

```bash
# Connect to Supabase and verify tables
psql "$DATABASE_URL" << EOF
-- List all tables
\dt

-- Check user table structure
\d "User"

-- Check blog table structure
\d "Blog"

-- Verify Row Level Security (RLS) is enabled
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public';
EOF

# ✅ All tables should be visible
```

#### Step 2B.3: Apply Row Level Security (RLS) Policies

```bash
# Run RLS setup scripts from database/
cd /home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service

# Apply RLS policies
psql "$DATABASE_URL" < database/rls-setup-corrected.sql

# Verify RLS coverage
psql "$DATABASE_URL" < database/verify-rls-coverage.sql

# ✅ RLS policies applied!
```

#### Step 2B.4: (Optional) Seed Initial Data

```bash
# If you have a seed script
npx prisma db seed

# Or manually insert test admin user
psql "$DATABASE_URL" << EOF
INSERT INTO "User" (id, email, name, role, "generationCount", "generationLimit", "createdAt", "updatedAt")
VALUES (
  gen_random_uuid(),
  'admin@yourdomain.com',
  'Admin User',
  'ADMIN',
  0,
  999999,
  NOW(),
  NOW()
);
EOF

# ✅ Database ready for production!
```

---

## 🔧 Phase 3: Backend Deployment

**Estimated Time:** 20-30 minutes

### Step 3.1: Configure Railway Environment Variables

```bash
# Option A: Via Railway Dashboard (Recommended for first time)
# 1. Go to Railway Dashboard: https://railway.app/dashboard
# 2. Select your project → backend service
# 3. Go to "Variables" tab
# 4. Add all variables below:

# Option B: Via Railway CLI (Faster for future deployments)
railway login

# Set variables one by one
railway variables set DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres"
railway variables set SUPABASE_URL="https://[PROJECT].supabase.co"
railway variables set SUPABASE_KEY="your_supabase_anon_key"
railway variables set REDIS_URL="redis://default:[PASSWORD]@[REGION].upstash.io:6379"
railway variables set OPENAI_API_KEY="sk-your-production-key"
railway variables set UNSPLASH_ACCESS_KEY="your_unsplash_key"
railway variables set JWT_SECRET="your-generated-secret-32-chars-min"
railway variables set NEXTAUTH_SECRET="your-generated-secret-32-chars-min"
railway variables set ENVIRONMENT="production"
railway variables set DEBUG="false"
railway variables set LOG_LEVEL="info"
railway variables set HTTPS_ENABLED="true"
railway variables set AWS_ACCESS_KEY_ID="your_aws_key"
railway variables set AWS_SECRET_ACCESS_KEY="your_aws_secret"
railway variables set AWS_S3_BUCKET="your-production-bucket"
railway variables set AWS_REGION="us-east-1"
railway variables set ENABLE_AI_IMAGE_GENERATION="false"
railway variables set ENABLE_HERO_IMAGE_GENERATION="false"
railway variables set ENABLE_CONTENT_IMAGE_INJECTION="false"

# ✅ All environment variables set!
```

**Full list of backend environment variables:**

```bash
# Database
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
SUPABASE_URL=https://[PROJECT].supabase.co
SUPABASE_KEY=your_supabase_anon_key

# Redis
REDIS_URL=redis://default:[PASSWORD]@[REGION].upstash.io:6379

# APIs
OPENAI_API_KEY=sk-your-production-key
UNSPLASH_ACCESS_KEY=your_unsplash_key

# AWS S3
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_S3_BUCKET=your-production-bucket
AWS_REGION=us-east-1

# Security
JWT_SECRET=your-generated-secret-32-chars-min
NEXTAUTH_SECRET=your-generated-secret-32-chars-min

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info
HTTPS_ENABLED=true

# Features
ENABLE_AI_IMAGE_GENERATION=false
ENABLE_HERO_IMAGE_GENERATION=false
ENABLE_CONTENT_IMAGE_INJECTION=false

# CORS (update after frontend deployed)
CORS_ORIGINS=https://your-frontend.vercel.app
```

### Step 3.2: Configure Railway Service Settings

**Important:** Railway needs to know where your code is and how to run it.

#### Via Railway Dashboard (Recommended for First Deployment)

```bash
# 1. Go to Railway Dashboard: https://railway.app/dashboard
# 2. Select your project → backend service
# 3. Click on "Settings" tab (top navigation)
# 4. Configure these sections in the right sidebar:

## Section: Source
- Root Directory: backend/
- Branch: main
- ✅ Save changes

## Section: Deploy  
- Start Command: python src/main.py
- Restart Policy: On Failure
- Max Retries: 10
- ✅ Save changes

## Section: Networking
- Health Check Path: /health
- Health Check Timeout: 30 seconds
- Port: (Railway auto-assigns via $PORT variable)
- ✅ Save changes

## Section: Build
- Builder: Nixpacks (default)
- Build Command: pip install -r requirements.txt
- ✅ Save changes (Railway usually auto-detects this)

# 5. Verify Railway reads PORT from environment
# Your backend/src/main.py should have:
#   port = int(os.environ.get("PORT", 5000))
```

#### Via railway.json (Alternative - Infrastructure as Code)

If you prefer configuration files, create `backend/railway.json`:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "python src/main.py",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

Then commit and push:
```bash
git add backend/railway.json
git commit -m "Add Railway configuration"
git push origin main
```

#### Verify Railway Configuration

```bash
# Check if Railway picked up your settings:
# 1. Go to Railway Dashboard → Your Service → Settings
# 2. Verify each section shows your configured values
# 3. Look for these indicators:
#    ✓ Root Directory: backend/
#    ✓ Start Command: python src/main.py
#    ✓ Health Check: /health

# ✅ Configuration verified! Ready to deploy.
```

### Step 3.3: Verify Backend Dockerfile

```bash
# Railway uses Docker to build your app. Verify Dockerfile exists:
ls -la backend/Dockerfile

# Should show:
# -rw-rw-r-- 1 user user 1234 Oct 15 12:00 backend/Dockerfile

# If it exists, Railway will use it automatically.
# If it doesn't exist, Railway will use Nixpacks auto-detection.

# ✅ Build configuration ready!
```

### Step 3.4: Deploy Backend to Railway

```bash
# Railway auto-deploys when you push to GitHub

# Method 1: Via GitHub (Recommended)
git add .
git commit -m "Configure production environment"
git push origin main

# Railway will:
# 1. Detect push
# 2. Build Docker image
# 3. Deploy to production
# 4. Run health checks

# Method 2: Via Railway CLI (Manual trigger)
cd backend
railway up

# Monitor deployment
railway logs

# Wait for deployment to complete (~2-5 minutes)

# ✅ Backend deployed! Check the logs for any errors.
```

### Step 3.4: Verify Backend Deployment

```bash
# Get your Railway URL from dashboard
# Example: https://bloggen-backend-production.up.railway.app

# Test health endpoint
curl https://your-backend.up.railway.app/health

# Expected response:
# {
#   "status": "healthy",
#   "timestamp": "2025-10-15T12:00:00Z",
#   "environment": "production"
# }

# Test database pool health
curl https://your-backend.up.railway.app/health/database-pool

# Expected response:
# {
#   "status": "healthy",
#   "pool": {
#     "initialized": true,
#     "closed": false,
#     "connections": 10
#   }
# }

# Test Redis connection
curl https://your-backend.up.railway.app/health/redis

# ✅ If all health checks pass, backend is ready!
```

---

## 🎨 Phase 4: Frontend Deployment

**Estimated Time:** 20-30 minutes

### Step 4.1: Configure Vercel Environment Variables

```bash
# Option A: Via Vercel Dashboard (Recommended for first time)
# 1. Go to Vercel Dashboard: https://vercel.com/dashboard
# 2. Select your project
# 3. Go to Settings → Environment Variables
# 4. Add all variables below (select Production environment)

# Option B: Via Vercel CLI
vercel login

# Link project
cd frontend-nextjs/blog-generator-ui
vercel link

# Set environment variables
vercel env add NEXT_PUBLIC_API_URL production
# When prompted, enter: https://your-backend.up.railway.app

vercel env add NEXTAUTH_URL production
# When prompted, enter: https://your-frontend.vercel.app

vercel env add NEXTAUTH_SECRET production
# When prompted, enter: [your-generated-secret]

vercel env add DATABASE_URL production
# When prompted, enter: postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres

vercel env add GOOGLE_CLIENT_ID production
# When prompted, enter: [your-google-client-id]

vercel env add GOOGLE_CLIENT_SECRET production
# When prompted, enter: [your-google-client-secret]

vercel env add GITHUB_ID production
# When prompted, enter: [your-github-client-id]

vercel env add GITHUB_SECRET production
# When prompted, enter: [your-github-client-secret]

vercel env add NODE_ENV production
# When prompted, enter: production

vercel env add NEXT_PUBLIC_APP_URL production
# When prompted, enter: https://your-frontend.vercel.app

vercel env add NEXT_PUBLIC_ENVIRONMENT production
# When prompted, enter: production

# ✅ All environment variables set!
```

**Full list of frontend environment variables:**

```bash
# API Endpoints
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app
NEXT_PUBLIC_WS_URL=wss://your-backend.up.railway.app

# NextAuth
NEXTAUTH_URL=https://your-frontend.vercel.app
NEXTAUTH_SECRET=your-generated-secret-32-chars-min

# Database
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres

# OAuth Providers (Production credentials)
GOOGLE_CLIENT_ID=your-production-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-production-google-client-secret
GITHUB_ID=your-production-github-app-client-id
GITHUB_SECRET=your-production-github-app-client-secret

# Application
NODE_ENV=production
NEXT_PUBLIC_APP_URL=https://your-frontend.vercel.app
NEXT_PUBLIC_ENVIRONMENT=production
```

### Step 4.2: Update OAuth Redirect URIs

**Important:** Update OAuth provider settings with production URLs.

**Google OAuth:**
```bash
# 1. Go to: https://console.cloud.google.com/apis/credentials
# 2. Select your OAuth 2.0 Client ID
# 3. Add Authorized redirect URIs:
#    https://your-frontend.vercel.app/api/auth/callback/google
#    https://yourdomain.com/api/auth/callback/google (if using custom domain)
# 4. Save changes
```

**GitHub OAuth:**
```bash
# 1. Go to: https://github.com/settings/developers
# 2. Select your OAuth App
# 3. Update Authorization callback URL:
#    https://your-frontend.vercel.app/api/auth/callback/github
#    https://yourdomain.com/api/auth/callback/github (if using custom domain)
# 4. Save changes
```

### Step 4.3: Deploy Frontend to Vercel

```bash
# Vercel auto-deploys when you push to GitHub

# Method 1: Via GitHub (Recommended)
git add .
git commit -m "Configure frontend production environment"
git push origin main

# Vercel will:
# 1. Detect push
# 2. Build Next.js app
# 3. Deploy to production
# 4. Run health checks

# Method 2: Via Vercel CLI (Manual trigger)
cd frontend-nextjs/blog-generator-ui
vercel --prod

# Monitor deployment
vercel logs

# Wait for deployment to complete (~3-7 minutes)

# ✅ Frontend deployed!
```

### Step 4.4: Update Backend CORS Origins

```bash
# Now that frontend is deployed, update backend CORS

# Via Railway Dashboard:
# 1. Go to Railway → Your project → backend service → Variables
# 2. Update CORS_ORIGINS variable:
CORS_ORIGINS=https://your-frontend.vercel.app,https://www.your-frontend.vercel.app

# Via Railway CLI:
railway variables set CORS_ORIGINS="https://your-frontend.vercel.app,https://www.your-frontend.vercel.app"

# Redeploy backend (Railway will auto-restart with new env var)

# ✅ CORS configured!
```

### Step 4.5: Verify Frontend Deployment

```bash
# Visit your frontend URL
# https://your-frontend.vercel.app

# Test checklist:
# 1. ✅ Homepage loads without errors
# 2. ✅ Login page accessible
# 3. ✅ Google OAuth works (try logging in)
# 4. ✅ GitHub OAuth works (try logging in)
# 5. ✅ Dashboard loads after login
# 6. ✅ No console errors in browser dev tools

# Check browser console (F12):
# - Should see successful API connections
# - No CORS errors
# - No 404 errors

# ✅ If all checks pass, frontend is ready!
```

---

## ✅ Phase 5: Verification & Testing

**Estimated Time:** 20-30 minutes

### Step 5.1: End-to-End Testing

```bash
# Test complete blog generation flow:

# 1. Sign up / Login
#    - Visit: https://your-frontend.vercel.app
#    - Click "Sign in with Google" or "Sign in with GitHub"
#    - Complete OAuth flow
#    - Verify redirect back to dashboard

# 2. Check user stats
#    - Dashboard should show:
#      - User role (FREE/PREMIUM/ADMIN)
#      - Generation count (0)
#      - Generation limit (3 for FREE tier)
#      - Previous blogs (empty)

# 3. Generate test blog
#    - Click "Generate New Blog"
#    - Enter topic: "The Future of AI in Healthcare"
#    - Click "Generate"
#    - Watch real-time updates via SSE:
#      ✓ Research phase
#      ✓ Content generation phase
#      ✓ Fact checking phase
#      ✓ Finalization phase
#    - Blog should appear in ~3-5 minutes

# 4. Verify blog content
#    - Click on generated blog
#    - Check blog contains:
#      ✓ Title
#      ✓ Hero image (Unsplash or placeholder)
#      ✓ Well-formatted content
#      ✓ Proper markdown rendering
#      ✓ Images integrated (if enabled)
#      ✓ Created timestamp

# 5. Check database
#    - User should have generationCount = 1
#    - Blog should be saved in database
#    - Audit logs should exist

# ✅ If all steps work, deployment successful!
```

### Step 5.2: Performance Testing

```bash
# Test API response times
curl -w "@curl-format.txt" -o /dev/null -s https://your-backend.up.railway.app/health

# Create curl-format.txt:
cat > curl-format.txt << 'EOF'
    time_namelookup:  %{time_namelookup}\n
       time_connect:  %{time_connect}\n
    time_appconnect:  %{time_appconnect}\n
   time_pretransfer:  %{time_pretransfer}\n
      time_redirect:  %{time_redirect}\n
 time_starttransfer:  %{time_starttransfer}\n
                    ----------\n
         time_total:  %{time_total}\n
EOF

# Expected response times:
# Health endpoint: < 200ms
# Database queries: < 500ms
# Blog generation: 180-300 seconds

# ✅ Performance acceptable if health checks < 500ms
```

### Step 5.3: Load Testing (Optional)

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test health endpoint (100 requests, 10 concurrent)
ab -n 100 -c 10 https://your-backend.up.railway.app/health

# Review results:
# - Requests per second: Should be > 50
# - Mean time per request: Should be < 500ms
# - Failed requests: Should be 0

# ✅ If RPS > 50 and no failures, good performance!
```

---

## 📊 Phase 6: Monitoring Setup

**Estimated Time:** 15-20 minutes

### Step 6.1: Railway Monitoring

```bash
# Built-in Railway monitoring:
# 1. Go to Railway Dashboard → Your project → Metrics
# 2. Review:
#    - CPU usage
#    - Memory usage
#    - Network traffic
#    - Request count
#    - Response times

# Set up alerts:
# 1. Go to Settings → Notifications
# 2. Connect Slack or Discord
# 3. Enable alerts for:
#    - Deployment failures
#    - High error rates
#    - Resource limits

# ✅ Railway monitoring configured!
```

### Step 6.2: Vercel Analytics

```bash
# Enable Vercel Analytics (free):
# 1. Go to Vercel Dashboard → Your project → Analytics
# 2. Click "Enable Analytics"
# 3. Add analytics package to your frontend:

cd frontend-nextjs/blog-generator-ui
npm install @vercel/analytics

# Add to layout:
# src/app/layout.tsx
# import { Analytics } from '@vercel/analytics/react';
# <Analytics />

git add .
git commit -m "Add Vercel Analytics"
git push

# ✅ Vercel analytics enabled!
```

### Step 6.3: Uptime Monitoring

```bash
# Set up free uptime monitoring with UptimeRobot:
# 1. Sign up: https://uptimerobot.com/
# 2. Add monitors:

#    Monitor 1: Frontend
#    URL: https://your-frontend.vercel.app
#    Type: HTTPS
#    Interval: 5 minutes

#    Monitor 2: Backend Health
#    URL: https://your-backend.up.railway.app/health
#    Type: HTTPS
#    Interval: 5 minutes

#    Monitor 3: Database Pool Health
#    URL: https://your-backend.up.railway.app/health/database-pool
#    Type: HTTPS
#    Interval: 10 minutes

# 3. Set up alerts:
#    - Email notifications
#    - Slack/Discord webhooks (optional)

# ✅ Uptime monitoring configured!
```

### Step 6.4: Error Tracking (Optional but Recommended)

```bash
# Set up Sentry for error tracking:
# 1. Sign up: https://sentry.io/
# 2. Create project for backend and frontend

# Backend:
cd backend
pip install sentry-sdk[fastapi]

# Add to backend/src/main.py:
# import sentry_sdk
# sentry_sdk.init(
#     dsn="your-backend-dsn",
#     environment="production",
#     traces_sample_rate=0.1,
# )

# Frontend:
cd frontend-nextjs/blog-generator-ui
npx @sentry/wizard@latest -i nextjs

# Follow wizard prompts

# Add environment variables:
railway variables set SENTRY_DSN="your-backend-dsn"
vercel env add NEXT_PUBLIC_SENTRY_DSN production
# Enter: your-frontend-dsn

# Deploy:
git add .
git commit -m "Add Sentry error tracking"
git push

# ✅ Error tracking configured!
```

---

## 🤖 Automated Deployment Scripts

All automation scripts are located in the `scripts/` directory and are ready to use!

### Script 1: Pre-Deployment Checker

**File:** `scripts/pre-deploy-check.sh`

Runs comprehensive checks before deployment to catch issues early.

**Usage:**
```bash
./scripts/pre-deploy-check.sh
```

**What it checks:**
- ✅ Git repository status
- ✅ Uncommitted changes
- ✅ Python/Node.js versions
- ✅ Critical files exist
- ✅ No hardcoded secrets
- ✅ No syntax errors
- ✅ Dependencies configured
- ✅ Docker configuration
- ✅ Documentation exists

**Output:**
- Detailed report of passed/failed checks
- Warnings for potential issues
- Exit code 0 if ready to deploy, 1 if issues found

---

### Script 2: Deploy to Production

**File:** `scripts/deploy-production.sh`

Automated deployment to Railway (backend) and Vercel (frontend).

**Usage:**
```bash
# Full deployment
./scripts/deploy-production.sh

# Backend only
./scripts/deploy-production.sh --backend-only

# Frontend only
./scripts/deploy-production.sh --frontend-only

# Skip pre-checks (not recommended)
./scripts/deploy-production.sh --skip-checks
```

**What it does:**
1. Runs pre-deployment checks (unless skipped)
2. Verifies required CLI tools
3. Commits and pushes changes
4. Deploys backend to Railway
5. Deploys frontend to Vercel
6. Runs health checks
7. Provides deployment summary
8. Saves deployment log

**Output:**
- Real-time deployment progress
- Deployment URLs
- Health check results
- Deployment log saved to `deployments/deployment-TIMESTAMP.log`

---

### Script 3: Rollback Deployment

**File:** `scripts/rollback.sh`

Safely rolls back to previous deployment if issues are detected.

**Usage:**
```bash
# Interactive rollback (prompts for target commit)
./scripts/rollback.sh

# Rollback backend only
./scripts/rollback.sh --backend

# Rollback frontend only
./scripts/rollback.sh --frontend

# Rollback to specific commit
./scripts/rollback.sh --to-commit abc123def
```

**What it does:**
1. Shows recent deployments/commits
2. Creates safety backup branch
3. Reverts code to target version
4. Pushes to trigger redeployment
5. Runs health checks
6. Saves rollback log

**Safety features:**
- Creates backup branch before rollback
- Uses `git revert` instead of `git reset` (safer)
- Requires confirmation at each step
- Validates target commit exists

**Output:**
- Rollback progress
- Backup branch name (for recovery)
- Health check results
- Rollback log saved to `rollbacks/rollback-TIMESTAMP.log`

---

### Script 4: Health Check

**File:** `scripts/health-check.sh`

Comprehensive health check for production deployment.

**Usage:**
```bash
# With URLs as arguments
./scripts/health-check.sh https://api.example.com https://example.com

# Interactive (prompts for URLs)
./scripts/health-check.sh
```

**What it checks:**
- ✅ Backend health endpoint
- ✅ Database pool status
- ✅ Redis connection
- ✅ Frontend homepage
- ✅ Authentication pages
- ✅ Static assets
- ✅ CORS configuration
- ✅ Protected endpoints
- ✅ SSL certificates
- ✅ Response times
- ✅ DNS resolution
- ✅ Connectivity

**Output:**
- Detailed check results
- Response times
- HTTP status codes
- Overall health score (%)
- Exit code 0 if healthy, 1 if critical issues

---

### Quick Reference

```bash
# 1. Before deploying
./scripts/pre-deploy-check.sh

# 2. Deploy to production
./scripts/deploy-production.sh

# 3. Verify deployment
./scripts/health-check.sh https://api.example.com https://example.com

# 4. If issues detected
./scripts/rollback.sh
```

### Automation Workflow

```
Development → pre-deploy-check.sh → deploy-production.sh
                     ↓                        ↓
                   [FAIL]                  [SUCCESS]
                     ↓                        ↓
                 Fix issues            health-check.sh
                                              ↓
                                         [ISSUES?]
                                              ↓
                                         rollback.sh
```

---

### Setting Up Automation

All scripts are already created and executable. To use them:

```bash
# Verify scripts are executable
ls -la scripts/

# If not executable, make them executable
chmod +x scripts/*.sh

# Test pre-deployment checks
./scripts/pre-deploy-check.sh

# Ready to deploy!
./scripts/deploy-production.sh
```

---

### CI/CD Integration (Future Enhancement)

These scripts can be integrated into GitHub Actions:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Pre-deployment checks
        run: ./scripts/pre-deploy-check.sh
      - name: Deploy
        run: ./scripts/deploy-production.sh --skip-checks
      - name: Health check
        run: ./scripts/health-check.sh ${{ secrets.BACKEND_URL }} ${{ secrets.FRONTEND_URL }}
```

---

## 🔧 Troubleshooting

### Issue: Backend deployment fails

**Symptoms:**
- Railway deployment fails
- Health checks timeout
- 500 errors

**Solutions:**
```bash
# 1. Check Railway logs
railway logs --tail 100

# 2. Verify environment variables
railway variables

# 3. Test database connection
railway run python -c "import asyncpg; print('OK')"

# 4. Check for missing dependencies
railway run pip list

# 5. Redeploy
railway up --detach
```

### Issue: Frontend can't connect to backend

**Symptoms:**
- CORS errors in browser console
- API requests fail with 403/404
- "Network error" messages

**Solutions:**
```bash
# 1. Verify NEXT_PUBLIC_API_URL is correct
vercel env ls

# 2. Check backend CORS_ORIGINS includes frontend URL
railway variables | grep CORS_ORIGINS

# 3. Update CORS if needed
railway variables set CORS_ORIGINS="https://your-frontend.vercel.app"

# 4. Clear Vercel cache and redeploy
vercel --prod --force
```

### Issue: Database connection fails

**Symptoms:**
- "Connection refused" errors
- "Too many connections" errors
- Timeout errors

**Solutions:**
```bash
# 1. Test direct connection
psql "$DATABASE_URL" -c "SELECT 1"

# 2. Check connection string format
echo $DATABASE_URL
# Should be: postgresql://postgres:password@host:5432/database

# 3. Verify Supabase is not paused
# Free tier pauses after 1 week of inactivity

# 4. Check connection pool settings
railway variables | grep DATABASE_URL

# 5. Restart backend
railway restart
```

### Issue: Redis connection fails

**Symptoms:**
- "Connection refused" errors
- SSE streaming doesn't work
- Task status not updating

**Solutions:**
```bash
# 1. Test direct connection
redis-cli -u "$REDIS_URL" PING

# 2. Check Upstash console for issues
# https://console.upstash.com/

# 3. Verify REDIS_URL format
echo $REDIS_URL
# Should be: redis://default:password@host:6379

# 4. Try REST API instead
railway variables set UPSTASH_REDIS_REST_URL="https://your-db.upstash.io"
railway variables set UPSTASH_REDIS_REST_TOKEN="your-token"

# 5. Restart backend
railway restart
```

### Issue: OAuth login fails

**Symptoms:**
- "Redirect URI mismatch" errors
- "Invalid client" errors
- Login redirects to error page

**Solutions:**
```bash
# 1. Verify OAuth redirect URIs in provider console

# Google:
# https://console.cloud.google.com/apis/credentials
# Authorized redirect URIs should include:
# https://your-frontend.vercel.app/api/auth/callback/google

# GitHub:
# https://github.com/settings/developers
# Authorization callback URL should be:
# https://your-frontend.vercel.app/api/auth/callback/github

# 2. Verify NEXTAUTH_URL matches your frontend URL
vercel env ls | grep NEXTAUTH_URL

# 3. Check NEXTAUTH_SECRET is set and matches between frontend/backend
vercel env ls | grep NEXTAUTH_SECRET
railway variables | grep NEXTAUTH_SECRET

# 4. Clear browser cookies and try again
```

---

## 📝 Post-Deployment Checklist

After successful deployment, verify:

### Immediate (Day 1)
- [ ] Frontend loads without errors
- [ ] Backend health checks passing
- [ ] User registration works
- [ ] User login works (Google OAuth)
- [ ] User login works (GitHub OAuth)
- [ ] Blog generation works end-to-end
- [ ] Real-time SSE updates working
- [ ] Images displaying correctly
- [ ] Database queries working
- [ ] Redis caching working
- [ ] Monitoring set up
- [ ] Error tracking set up
- [ ] Uptime alerts configured

### Week 1
- [ ] Monitor error rates (should be < 1%)
- [ ] Check response times (should be < 2s avg)
- [ ] Review logs for warnings
- [ ] Test with 10+ blogs
- [ ] Verify costs match projections
- [ ] Check Upstash Redis usage
- [ ] Check Railway usage
- [ ] Verify backups running (Supabase)
- [ ] Test rollback procedure
- [ ] Document any issues

### Month 1
- [ ] Performance optimization
- [ ] Cost optimization
- [ ] User feedback collection
- [ ] Scale up if needed
- [ ] Security audit
- [ ] Update documentation

---

## 🎯 Success Criteria

Your deployment is successful when:

✅ **Functionality**
- Users can register and login
- Blog generation works consistently
- Real-time updates via SSE working
- All CRUD operations functional

✅ **Performance**
- Health checks < 500ms
- Blog generation < 5 minutes
- Page loads < 2 seconds
- No memory leaks

✅ **Reliability**
- Uptime > 99%
- Error rate < 1%
- Zero data loss
- Successful rollback capability

✅ **Monitoring**
- Logs accessible and searchable
- Alerts configured and tested
- Metrics tracked and dashboards set up
- Cost tracking enabled

---

## 🚀 Next Steps

After successful deployment:

1. **Custom Domain** (Optional)
   - Purchase domain from Namecheap, Google Domains, etc.
   - Add to Vercel (frontend)
   - Add to Railway (backend)
   - Configure DNS

2. **CI/CD Optimization**
   - Set up staging environment
   - Add automated tests to CI
   - Implement blue-green deployments
   - Add deployment previews

3. **Performance Optimization**
   - Enable CDN for static assets
   - Implement caching strategies
   - Optimize database queries
   - Add connection pooling

4. **Security Hardening**
   - Enable rate limiting
   - Add DDoS protection
   - Implement WAF rules
   - Set up security scanning

5. **Feature Enhancements**
   - Add more OAuth providers
   - Implement payment system (Stripe)
   - Add email notifications
   - Build admin dashboard

---

## 📚 Resources

- **Railway Docs**: https://docs.railway.app/
- **Vercel Docs**: https://vercel.com/docs
- **Upstash Docs**: https://docs.upstash.com/
- **Supabase Docs**: https://supabase.com/docs
- **Next.js Docs**: https://nextjs.org/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com/

---

**Congratulations! 🎉**

You've successfully deployed your CrewAI blog generation service to production!

---

*Last updated: October 15, 2025*
