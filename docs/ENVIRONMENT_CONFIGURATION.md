# 🔧 Environment Configuration Guide

**Last Updated:** October 14, 2025

---

## 📋 Overview

This project uses **different configurations** for local development and production deployment:

- **Local Development**: Uses local PostgreSQL container + local Redis server
- **Production**: Uses Supabase PostgreSQL + Upstash Redis (managed cloud services)

---

## 🏠 Local Development Setup

### Environment Files

```bash
# Backend
backend/.env.local          # Your local config (git-ignored)
backend/.env.local.example  # Template to copy from

# Frontend
frontend-nextjs/blog-generator-ui/.env.local          # Your local config (git-ignored)
frontend-nextjs/blog-generator-ui/.env.local.example  # Template to copy from
```

### Setup Instructions

```bash
# 1. Copy example files
cp backend/.env.local.example backend/.env.local
cp frontend-nextjs/blog-generator-ui/.env.local.example frontend-nextjs/blog-generator-ui/.env.local

# 2. Edit with your local credentials
nano backend/.env.local
nano frontend-nextjs/blog-generator-ui/.env.local

# 3. Start local services
# PostgreSQL (if using Docker)
docker-compose -f docker-compose.dev.yml up postgres -d

# Redis (system install)
redis-server  # Already running on your system

# 4. Verify connections
redis-cli ping  # Should return PONG
psql postgresql://postgres:postgres@localhost:5432/bloggen_dev -c "SELECT 1"
```

### Local Environment Configuration

**Backend (.env.local):**
```bash
# Database - Local PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bloggen_dev

# Redis - Local Redis Server
REDIS_URL=redis://localhost:6379

# Security - Development secrets (not production-grade)
JWT_SECRET=local-dev-secret-min-32-characters-long

# Application
ENVIRONMENT=development
DEBUG=true
HTTPS_ENABLED=true
```

**Frontend (.env.local):**
```bash
# API - Local Backend
NEXT_PUBLIC_API_URL=https://localhost:5000

# Database - Local PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bloggen_dev

# Auth
NEXTAUTH_URL=https://localhost:3000
```

---

## 🌐 Production Setup

### Environment Files

```bash
# Backend
backend/.env.production          # Production config (git-ignored, set in Railway)
backend/.env.production.example  # Template for reference

# Frontend
frontend-nextjs/blog-generator-ui/.env.production          # Production config (git-ignored, set in Vercel)
frontend-nextjs/blog-generator-ui/.env.production.example  # Template for reference
```

### Production Environment Configuration

**Backend (Set in Railway Dashboard):**
```bash
# Database - Supabase PostgreSQL (Managed)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
SUPABASE_URL=https://[PROJECT].supabase.co
SUPABASE_KEY=your_production_supabase_anon_key

# Redis - Upstash Redis (Managed)
REDIS_URL=redis://default:[PASSWORD]@[REGION].upstash.io:6379

# Security - Strong production secrets
JWT_SECRET=your-super-secure-production-secret-min-32-chars
NEXTAUTH_SECRET=your-super-secure-nextauth-secret-min-32-chars

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info
```

**Frontend (Set in Vercel Dashboard):**
```bash
# API - Production Backend
NEXT_PUBLIC_API_URL=https://api.yourdomain.com

# Database - Supabase PostgreSQL
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres

# Auth
NEXTAUTH_URL=https://yourdomain.com
NEXTAUTH_SECRET=your-super-secure-production-nextauth-secret-min-32-chars
```

---

## 🔄 Environment Switching Workflow

### Development Workflow (Daily Use)

```bash
# 1. Ensure local services running
redis-cli ping  # Check Redis
psql $DATABASE_URL -c "SELECT 1"  # Check PostgreSQL

# 2. Start backend (uses .env.local automatically)
cd backend
source .venv/bin/activate
python src/main.py

# 3. Start frontend (uses .env.local automatically)
cd frontend-nextjs/blog-generator-ui
npm run dev

# 4. Access locally
# Frontend: https://localhost:3000
# Backend: https://localhost:5000
```

### Production Deployment Workflow

```bash
# 1. Commit code changes (NO environment files!)
git add src/
git commit -m "Add new feature"
git push origin main

# 2. Automatic deployment
# Railway: Auto-deploys backend (uses Railway env vars)
# Vercel: Auto-deploys frontend (uses Vercel env vars)

# 3. Verify production
# Frontend: https://yourdomain.com
# Backend: https://api.yourdomain.com/health
```

---

## 🔐 Security Best Practices

### ✅ DO

```bash
✅ Use .env.local for local development
✅ Use platform dashboards (Railway/Vercel) for production secrets
✅ Keep .env.*.example files in git (without secrets)
✅ Generate strong secrets for production:
   openssl rand -base64 32
✅ Use different secrets for dev vs production
✅ Rotate secrets regularly
```

### ❌ DON'T

```bash
❌ Commit .env.local or .env.production to git
❌ Use same secrets in dev and production
❌ Share production secrets in Slack/email
❌ Use weak secrets like "secret123"
❌ Hardcode secrets in source code
❌ Copy production secrets to local .env
```

---

## 🗂️ File Structure

```
bloggen-web-service/
│
├── backend/
│   ├── .env.local                    # ❌ Git-ignored (your local config)
│   ├── .env.local.example            # ✅ In git (template)
│   ├── .env.production               # ❌ Git-ignored (not needed locally)
│   ├── .env.production.example       # ✅ In git (template)
│   └── .gitignore                    # Contains: .env.local, .env.production
│
├── frontend-nextjs/blog-generator-ui/
│   ├── .env.local                    # ❌ Git-ignored (your local config)
│   ├── .env.local.example            # ✅ In git (template)
│   ├── .env.production               # ❌ Git-ignored (not needed locally)
│   ├── .env.production.example       # ✅ In git (template)
│   └── .gitignore                    # Contains: .env.local, .env.production
│
└── docs/
    └── ENVIRONMENT_CONFIGURATION.md  # ✅ This file
```

---

## 🧪 Testing Configuration

### Test Local Configuration

```bash
# Backend - Check environment variables
cd backend
source .venv/bin/activate
python -c "
from dotenv import load_dotenv
import os
load_dotenv('.env.local')
print('DATABASE_URL:', os.getenv('DATABASE_URL'))
print('REDIS_URL:', os.getenv('REDIS_URL'))
print('ENVIRONMENT:', os.getenv('ENVIRONMENT'))
"

# Expected output:
# DATABASE_URL: postgresql://postgres:postgres@localhost:5432/bloggen_dev
# REDIS_URL: redis://localhost:6379
# ENVIRONMENT: development
```

### Test Production Configuration (in Railway/Vercel)

```bash
# Railway CLI - Check backend env vars
railway run env

# Vercel CLI - Check frontend env vars
vercel env pull
```

---

## 🚀 Quick Reference

### Local Development Commands

```bash
# Start everything
make dev  # Starts both frontend and backend

# Or manually:
# Terminal 1: Backend
cd backend && source .venv/bin/activate && python src/main.py

# Terminal 2: Frontend
cd frontend-nextjs/blog-generator-ui && npm run dev

# Terminal 3: Check Redis
redis-cli monitor

# Terminal 4: Check PostgreSQL
psql postgresql://postgres:postgres@localhost:5432/bloggen_dev
```

### Production Deployment Commands

```bash
# Deploy backend to Railway
git push origin main  # Auto-deploys

# Deploy frontend to Vercel
git push origin main  # Auto-deploys

# Manual deploy (if needed)
railway up  # Backend
vercel --prod  # Frontend
```

---

## 🔍 Troubleshooting

### Issue: "Can't connect to Redis"

**Local:**
```bash
# Check if Redis running
redis-cli ping

# If not running
redis-server

# Check port
sudo lsof -i :6379
```

**Production:**
```bash
# Check Upstash connection
redis-cli -u "redis://default:[PASSWORD]@[REGION].upstash.io:6379" PING

# Verify env var in Railway
railway run env | grep REDIS_URL
```

### Issue: "Database connection failed"

**Local:**
```bash
# Check if PostgreSQL running
psql postgresql://postgres:postgres@localhost:5432/bloggen_dev -c "SELECT 1"

# If not running (Docker)
docker-compose -f docker-compose.dev.yml up postgres -d
```

**Production:**
```bash
# Check Supabase connection
psql "$DATABASE_URL" -c "SELECT 1"

# Verify env var in Railway/Vercel
railway run env | grep DATABASE_URL
vercel env pull
```

### Issue: "Wrong environment variables loaded"

```bash
# Backend - Check which .env file is loaded
cd backend
python -c "
import os
print('Environment:', os.getenv('ENVIRONMENT'))
print('Database:', os.getenv('DATABASE_URL')[:30] + '...')
"

# Should show:
# Local: ENVIRONMENT=development, DATABASE_URL=postgresql://postgres@localhost...
# Prod: ENVIRONMENT=production, DATABASE_URL=postgresql://postgres@db.*.supabase.co...
```

---

## 📚 Related Documentation

- [PRODUCTION_DEPLOYMENT_PROPOSAL.md](../PRODUCTION_DEPLOYMENT_PROPOSAL.md) - Full deployment guide
- [LOCAL_DEVELOPMENT_SETUP.md](./LOCAL_DEVELOPMENT_SETUP.md) - Local setup guide
- [HTTPS_SECURITY.md](./HTTPS_SECURITY.md) - SSL/TLS configuration

---

## ✅ Environment Checklist

### Local Development Setup
- [ ] Copied `.env.local.example` to `.env.local` (both backend and frontend)
- [ ] Updated `.env.local` with your API keys
- [ ] Local PostgreSQL running and accessible
- [ ] Local Redis running and accessible
- [ ] Backend starts without errors
- [ ] Frontend connects to backend successfully
- [ ] Can generate test blog locally

### Production Deployment Setup
- [ ] Signed up for Supabase (PostgreSQL)
- [ ] Signed up for Upstash (Redis)
- [ ] Signed up for Railway (Backend hosting)
- [ ] Signed up for Vercel (Frontend hosting)
- [ ] Added all environment variables to Railway dashboard
- [ ] Added all environment variables to Vercel dashboard
- [ ] Generated strong production secrets (32+ characters)
- [ ] Configured custom domain (optional)
- [ ] Tested production deployment end-to-end

---

**Summary:**
- 🏠 **Local**: Keep using your current setup (local PostgreSQL + local Redis)
- 🌐 **Production**: Deploy to managed services (Supabase + Upstash)
- 🔒 **Security**: Never commit secrets, use platform dashboards
- 🔄 **Workflow**: Push to git → Auto-deploy to production

---

*Last updated: October 14, 2025*
