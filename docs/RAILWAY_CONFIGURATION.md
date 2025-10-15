# 🚂 Railway Configuration Guide

**Last Updated:** October 15, 2025  
**Service:** Backend (Python Flask + CrewAI)  
**Platform:** Railway.app

---

## 🎯 Quick Navigation Guide

When you're in Railway's Settings interface, you'll see these sections in the right sidebar:

```
Settings (top tab)
├── Source          ← Set root directory here
├── Networking      ← Set health check here
├── Build           ← Usually auto-detected
├── Deploy          ← Set start command here
├── Config-as-code  ← Alternative method
└── Danger          ← Service deletion
```

---

## 📍 Step-by-Step Configuration

### 1. Source Section

**Where:** Settings → Source (right sidebar)

```bash
Root Directory: backend/
# This tells Railway your code is in the backend/ folder

Branch: main
# Deploy from main branch (or your production branch)

✅ Click "Save" after setting
```

**What this does:** Railway will look for your code starting from `backend/` instead of the project root.

---

### 2. Deploy Section 🎯 IMPORTANT

**Where:** Settings → Deploy (right sidebar)

```bash
Start Command: python src/main.py
# This is how Railway starts your application

Restart Policy: On Failure
# Automatically restart if app crashes

Max Retries: 10
# Try up to 10 times before giving up

✅ Click "Save" after setting
```

**What this does:** Railway runs `python src/main.py` from inside the `backend/` directory to start your Flask server.

**Common mistake:** Forgetting to set this - Railway might try to guess and fail.

---

### 3. Networking Section

**Where:** Settings → Networking (right sidebar)

```bash
Health Check Path: /health
# Railway pings this endpoint to verify app is running

Health Check Timeout: 30
# Wait 30 seconds for health check to respond

Port: (Auto-assigned)
# Railway sets $PORT environment variable
# Your code should read: port = int(os.environ.get("PORT", 5000))

Public Networking:
Domain: bloggen-web-service-production.up.railway.app
# This is auto-generated, you can customize it

✅ Click "Save" after setting
```

**What this does:** Railway continuously checks if your app is healthy by calling `https://your-app.railway.app/health` every few minutes.

---

### 4. Build Section

**Where:** Settings → Build (right sidebar)

```bash
Builder: Nixpacks (default)
# Railway auto-detects Python and uses Nixpacks

Build Command: pip install -r requirements.txt
# Usually auto-detected from requirements.txt

Docker Image: (optional)
# If you have backend/Dockerfile, Railway will use it automatically

✅ Usually no changes needed here - Railway auto-detects
```

**What this does:** Railway builds your Python environment and installs dependencies before running your app.

---

## 🔐 Environment Variables

**Where:** Variables tab (top navigation, next to Settings)

**Critical variables to set:**

```bash
# Database (from Supabase)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
SUPABASE_URL=https://[PROJECT].supabase.co
SUPABASE_KEY=your-anon-key

# Redis (from Upstash)
REDIS_URL=redis://default:[PASSWORD]@[REGION].upstash.io:6379

# APIs
OPENAI_API_KEY=sk-your-production-key
UNSPLASH_ACCESS_KEY=your-unsplash-key

# Security (generate with: openssl rand -base64 32)
JWT_SECRET=your-generated-secret-32-chars-min
NEXTAUTH_SECRET=your-generated-secret-32-chars-min

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info

# Features
ENABLE_AI_IMAGE_GENERATION=false
ENABLE_HERO_IMAGE_GENERATION=false
ENABLE_CONTENT_IMAGE_INJECTION=false

# AWS S3 (optional)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_S3_BUCKET=your-bucket
AWS_REGION=us-east-1

# CORS (update after frontend deployed)
CORS_ORIGINS=https://your-frontend.vercel.app
```

---

## 🛠️ Alternative: Configuration as Code

If you prefer infrastructure-as-code, create `backend/railway.json`:

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

Railway will automatically detect and use this configuration.

---

## ✅ Verification Checklist

After configuration, verify these in Railway Dashboard:

```bash
# Settings → Source
✓ Root Directory shows: backend/

# Settings → Deploy  
✓ Start Command shows: python src/main.py

# Settings → Networking
✓ Health Check Path shows: /health

# Variables tab
✓ DATABASE_URL is set
✓ REDIS_URL is set
✓ OPENAI_API_KEY is set
✓ All other required variables are set

# Deployments tab
✓ Latest deployment succeeded
✓ Health checks passing
✓ Logs show no errors
```

---

## 🔍 Testing Your Configuration

### 1. Test Health Endpoint
```bash
# Get your Railway URL from dashboard
# Example: https://bloggen-backend-production.up.railway.app

curl https://your-backend.up.railway.app/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-10-15T12:00:00Z",
  "environment": "production"
}
```

### 2. Check Database Pool
```bash
curl https://your-backend.up.railway.app/health/database-pool

# Expected response:
{
  "status": "healthy",
  "pool": {
    "initialized": true,
    "closed": false
  }
}
```

### 3. Check Redis
```bash
curl https://your-backend.up.railway.app/health/redis

# Expected response:
{
  "status": "healthy",
  "redis": {
    "connected": true
  }
}
```

---

## 🐛 Common Issues & Solutions

### Issue: "Application failed to start"
**Solution:**
1. Check Start Command is set to: `python src/main.py`
2. Verify Root Directory is: `backend/`
3. Check logs: `railway logs --tail 100`

### Issue: "Health check failing"
**Solution:**
1. Verify Health Check Path is: `/health`
2. Test locally: `curl http://localhost:5000/health`
3. Check backend logs for errors

### Issue: "Module not found errors"
**Solution:**
1. Verify `requirements.txt` exists in `backend/`
2. Check build logs for pip install errors
3. Redeploy: `railway up`

### Issue: "Database connection errors"
**Solution:**
1. Verify `DATABASE_URL` in Variables tab
2. Test connection from Supabase dashboard
3. Check if IP whitelisting needed (Supabase allows all by default)

### Issue: "Redis connection errors"
**Solution:**
1. Verify `REDIS_URL` format: `redis://default:[PASSWORD]@[HOST]:6379`
2. Test from Upstash dashboard
3. Check if TLS is required

---

## 📚 Railway Resources

- **Dashboard:** https://railway.app/dashboard
- **Documentation:** https://docs.railway.app/
- **CLI Reference:** https://docs.railway.app/develop/cli
- **Discord Support:** https://discord.gg/railway

---

## 🎯 Quick Commands

```bash
# View current configuration
railway status

# View logs
railway logs --tail

# Restart service
railway restart

# Redeploy
railway up

# Open dashboard
railway open

# List variables
railway variables
```

---

**Need help?** Check the full deployment guide: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
