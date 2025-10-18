# 🚂 Railway Environment Variables Configuration

**Last Updated:** October 15, 2025  
**For:** Production Deployment

---

## ✅ Required Environment Variables for Railway

Copy these into **Railway Dashboard → Your Service → Variables**

### 🔐 Database (Supabase)
```bash
# Get from: Supabase Dashboard → Settings → Database → Connection String
# Use "Connection pooling" for serverless (port 6543)
DATABASE_URL=postgresql://postgres.agaejevkyzufcqptatdw:[PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

**⚠️ Important:** Your current `.env` has incorrect format:
- ❌ `postgres::PASSWORD` (double colon)
- ✅ Should be `postgres.agaejevkyzufcqptatdw:PASSWORD` (single colon with project ref)

---

### 🔴 Redis (Upstash)
```bash
# CRITICAL: Use 'rediss://' (double-s) for TLS/SSL
# Get from: https://console.upstash.com/ → eternal-duck-8525 → Connect
REDIS_URL=rediss://default:ASFNAAImcDI3ZWU5NTQxNmNjNjQ0MjNkYjY0YTk4OTliNjFlNTI5M3AyODUyNQ@eternal-duck-8525.upstash.io:6379
```

**Why `rediss://` not `redis://`?**
- Upstash requires TLS/SSL in production
- Single `redis://` = plain TCP (no encryption)
- Double `rediss://` = TLS/SSL encrypted

**Optional REST API variables (not needed for your setup):**
```bash
# Only if you want HTTP-based Redis access
UPSTASH_REDIS_REST_URL=https://eternal-duck-8525.upstash.io
UPSTASH_REDIS_REST_TOKEN=AiFNAAIgcDKY4ZpzWSnwJwryTzxLxZS0kWYBiFIvIuImyZ0PLUv1uQ
```

---

### 🤖 AI APIs
```bash
# OpenAI (for GPT models)
OPENAI_API_KEY=sk-proj-YOUR_OPENAI_KEY_HERE

# Google Gemini (for cost-effective models)
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY_HERE

# Serper (for web search)
SERPER_API_KEY=YOUR_SERPER_KEY_HERE

# Unsplash (for free images)
UNSPLASH_ACCESS_KEY=YOUR_UNSPLASH_ACCESS_KEY
UNSPLASH_SECRET_KEY=YOUR_UNSPLASH_SECRET_KEY
```

---

### ☁️ AWS S3 (Image Storage)
```bash
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY
AWS_S3_BUCKET_NAME=blog-hero-images-bloggen-app
AWS_S3_REGION=eu-west-3
```

---

### 🔒 Security & Authentication
```bash
# Must match frontend NEXTAUTH_SECRET
NEXTAUTH_SECRET=mOm6uXr4/5KEZSQ/vm6Okfz0/kfEEBZBP1DS50cvD8Q=
JWT_SECRET=mOm6uXr4/5KEZSQ/vm6Okfz0/kfEEBZBP1DS50cvD8Q=
```

---

### ⚙️ Application Configuration
```bash
# Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info

# HTTPS (Railway provides HTTPS automatically)
FORCE_HTTPS=false

# Features (AI image generation)
ENABLE_AI_IMAGE_GENERATION=true
ENABLE_HERO_IMAGE_GENERATION=true
ENABLE_CONTENT_IMAGE_INJECTION=true
```

---

### 🤖 Model Configuration (Gemini for Cost Savings)
```bash
# Content generation models
CONTENT_MODEL=gemini/gemini-2.5-flash-lite
FINALIZATION_MODEL=gemini/gemini-2.5-flash-lite

# Research & fact checking
RESEARCH_MODEL=gemini/gemini-2.5-flash-lite
FACT_CHECK_MODEL=gemini/gemini-2.5-flash-lite

# Default models
DEFAULT_MODEL=gemini/gemini-2.5-flash-lite
SUMMARY_MODEL=gemini/gemini-2.5-flash-lite
```

---

### 🌐 CORS & Frontend URLs (Update after Vercel deployment)
```bash
# Update these once you deploy frontend to Vercel
FRONTEND_URL=https://your-app.vercel.app
NEXTAUTH_URL=https://your-app.vercel.app
PRODUCTION_DOMAINS=https://your-app.vercel.app
CORS_ORIGINS=https://your-app.vercel.app
```

---

## 🎯 Quick Copy-Paste for Railway

**Step 1:** Go to Railway Dashboard → Your Service → Variables

**Step 2:** Add these one by one (or use bulk add):

```bash
DATABASE_URL=postgresql://postgres.agaejevkyzufcqptatdw:[GET-CORRECT-PASSWORD-FROM-SUPABASE]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
REDIS_URL=rediss://default:ASFNAAImcDI3ZWU5NTQxNmNjNjQ0MjNkYjY0YTk4OTliNjFlNTI5M3AyODUyNQ@eternal-duck-8525.upstash.io:6379
OPENAI_API_KEY=[YOUR_OPENAI_API_KEY]
GOOGLE_API_KEY=[YOUR_GOOGLE_API_KEY]
SERPER_API_KEY=[YOUR_SERPER_API_KEY]
UNSPLASH_ACCESS_KEY=[YOUR_UNSPLASH_ACCESS_KEY]
UNSPLASH_SECRET_KEY=[YOUR_UNSPLASH_SECRET_KEY]
AWS_ACCESS_KEY_ID=[YOUR_AWS_ACCESS_KEY_ID]
AWS_SECRET_ACCESS_KEY=[YOUR_AWS_SECRET_ACCESS_KEY]
AWS_S3_BUCKET_NAME=blog-hero-images-bloggen-app
AWS_S3_REGION=eu-west-3
NEXTAUTH_SECRET=mOm6uXr4/5KEZSQ/vm6Okfz0/kfEEBZBP1DS50cvD8Q=
JWT_SECRET=mOm6uXr4/5KEZSQ/vm6Okfz0/kfEEBZBP1DS50cvD8Q=
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info
FORCE_HTTPS=false
ENABLE_AI_IMAGE_GENERATION=true
ENABLE_HERO_IMAGE_GENERATION=true
ENABLE_CONTENT_IMAGE_INJECTION=true
CONTENT_MODEL=gemini/gemini-2.5-flash-lite
FINALIZATION_MODEL=gemini/gemini-2.5-flash-lite
RESEARCH_MODEL=gemini/gemini-2.5-flash-lite
FACT_CHECK_MODEL=gemini/gemini-2.5-flash-lite
DEFAULT_MODEL=gemini/gemini-2.5-flash-lite
SUMMARY_MODEL=gemini/gemini-2.5-flash-lite
```

---

## 🔍 Verification

After setting all variables, check Railway logs for:

```bash
✅ Should see:
- ✅ Redis connection successful
- ✅ Database pool initialized
- ✅ Server started on port 5000

❌ Should NOT see:
- Network is unreachable
- Connection refused
- Authentication failed
```

---

## 📚 Related Documentation

- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - Full deployment walkthrough
- [RAILWAY_CONFIGURATION.md](./RAILWAY_CONFIGURATION.md) - Railway-specific setup
- [.env.production.example](../backend/.env.production.example) - Production template

---

**Note:** Replace `[GET-CORRECT-PASSWORD-FROM-SUPABASE]` with your actual Supabase password from the dashboard.
