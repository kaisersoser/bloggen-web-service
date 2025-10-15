# 🚀 Quick Deployment Reference

**Last Updated:** October 15, 2025

---

## 📋 Quick Commands

### Initial Setup (One-time)
```bash
# 1. Sign up for services
#    - Supabase: https://supabase.com/
#    - Upstash: https://console.upstash.com/
#    - Railway: https://railway.app/
#    - Vercel: https://vercel.com/

# 2. Install CLI tools
npm install -g vercel @railway/cli

# 3. Login to services
railway login
vercel login
```

### Pre-Deployment
```bash
# Run pre-deployment checks
./scripts/pre-deploy-check.sh

# If checks pass, proceed with deployment
```

### Deploy to Production
```bash
# Full deployment (backend + frontend)
./scripts/deploy-production.sh

# Backend only
./scripts/deploy-production.sh --backend-only

# Frontend only
./scripts/deploy-production.sh --frontend-only

# Skip pre-checks (not recommended)
./scripts/deploy-production.sh --skip-checks
```

### Health Checks
```bash
# Check production health
./scripts/health-check.sh https://api.yourdomain.com https://yourdomain.com

# Or let it prompt you for URLs
./scripts/health-check.sh
```

### Rollback
```bash
# Rollback to previous deployment
./scripts/rollback.sh

# Rollback backend only
./scripts/rollback.sh --backend

# Rollback frontend only
./scripts/rollback.sh --frontend

# Rollback to specific commit
./scripts/rollback.sh --to-commit abc123
```

---

## 🔧 Manual Deployment

### Backend (Railway)
```bash
cd backend
railway up
railway logs
```

### Frontend (Vercel)
```bash
cd frontend-nextjs/blog-generator-ui
vercel --prod
vercel logs
```

---

## 🔍 Monitoring Commands

### Railway (Backend)
```bash
# View logs
railway logs

# View logs (follow)
railway logs --tail

# Check status
railway status

# List environment variables
railway variables

# Open dashboard
railway open
```

### Vercel (Frontend)
```bash
# View logs
vercel logs

# View logs (follow)
vercel logs --follow

# List deployments
vercel ls

# List environment variables
vercel env ls

# Open dashboard
vercel
```

---

## 🐛 Troubleshooting

### Backend Issues
```bash
# 1. Check logs
railway logs --tail 100

# 2. Verify environment variables
railway variables | grep -E "DATABASE_URL|REDIS_URL|OPENAI_API_KEY"

# 3. Test health endpoint
curl https://your-backend.up.railway.app/health

# 4. Restart service
railway restart

# 5. Redeploy
cd backend && railway up
```

### Frontend Issues
```bash
# 1. Check logs
vercel logs --follow

# 2. Verify environment variables
vercel env ls

# 3. Test homepage
curl https://your-frontend.vercel.app

# 4. Clear cache and redeploy
vercel --prod --force

# 5. Check build logs
vercel inspect
```

### Database Issues
```bash
# Test Supabase connection
psql "postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres" -c "SELECT 1"

# Check pool status
curl https://your-backend.up.railway.app/health/database-pool
```

### Redis Issues
```bash
# Test Upstash connection
redis-cli -u "redis://default:[PASSWORD]@[REGION].upstash.io:6379" PING

# Check Redis health
curl https://your-backend.up.railway.app/health/redis
```

---

## 📊 Environment Variables

### Backend Environment Variables
```bash
# Database
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
SUPABASE_URL=https://[PROJECT].supabase.co
SUPABASE_KEY=your_key

# Redis
REDIS_URL=redis://default:[PASSWORD]@[REGION].upstash.io:6379

# APIs
OPENAI_API_KEY=sk-your-key
UNSPLASH_ACCESS_KEY=your_key

# AWS S3
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_S3_BUCKET=your-bucket
AWS_REGION=us-east-1

# Security
JWT_SECRET=your-secret-32-chars-min
NEXTAUTH_SECRET=your-secret-32-chars-min

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info
HTTPS_ENABLED=true

# Features
ENABLE_AI_IMAGE_GENERATION=false
ENABLE_HERO_IMAGE_GENERATION=false
ENABLE_CONTENT_IMAGE_INJECTION=false

# CORS
CORS_ORIGINS=https://your-frontend.vercel.app
```

### Frontend Environment Variables
```bash
# API
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app

# NextAuth
NEXTAUTH_URL=https://your-frontend.vercel.app
NEXTAUTH_SECRET=your-secret-32-chars-min

# Database
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres

# OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-secret
GITHUB_ID=your-github-id
GITHUB_SECRET=your-secret

# Application
NODE_ENV=production
NEXT_PUBLIC_APP_URL=https://your-frontend.vercel.app
NEXT_PUBLIC_ENVIRONMENT=production
```

---

## 🔐 Security Checklist

- [ ] Strong secrets (32+ characters)
- [ ] OAuth redirect URIs updated
- [ ] CORS origins configured
- [ ] Environment variables set in dashboards (not in code)
- [ ] SSL certificates valid
- [ ] Rate limiting enabled
- [ ] Database RLS enabled
- [ ] No secrets in git history

---

## 📈 Performance Benchmarks

### Expected Response Times
- Health endpoint: < 500ms
- API endpoints: < 1s
- Blog generation: 180-300s
- Frontend page load: < 2s

### Expected Uptime
- Target: 99.9%
- Acceptable: 99.5%
- Critical: < 99%

---

## 💰 Cost Estimates

### MVP Scale (20-50 blogs/month)
- Vercel: $0
- Railway: $8-12
- Upstash: $0
- Supabase: $0
- AWS S3: $1-2
- OpenAI: $10-25
- **Total: $20-40/month**

### Growth Scale (100 blogs/month)
- Vercel: $20
- Railway: $15
- Upstash: $3-5
- Supabase: $0
- AWS S3: $3
- OpenAI: $50
- **Total: $91-93/month**

---

## 📚 Documentation Links

- **Full Deployment Guide**: [docs/DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- **Environment Configuration**: [docs/ENVIRONMENT_CONFIGURATION.md](./ENVIRONMENT_CONFIGURATION.md)
- **Deployment Proposal**: [PRODUCTION_DEPLOYMENT_PROPOSAL.md](../PRODUCTION_DEPLOYMENT_PROPOSAL.md)

---

## 🆘 Emergency Contacts

### Service Status Pages
- Railway: https://status.railway.app/
- Vercel: https://www.vercel-status.com/
- Upstash: https://status.upstash.com/
- Supabase: https://status.supabase.com/

### Support
- Railway: https://railway.app/help
- Vercel: https://vercel.com/support
- Upstash: https://upstash.com/docs/support
- Supabase: https://supabase.com/docs/support

---

## 🎯 Deployment Workflow

```
┌─────────────────────────────────────────────────────────┐
│                   DEPLOYMENT WORKFLOW                    │
└─────────────────────────────────────────────────────────┘

1. Development
   ├─ Work on feature branch
   ├─ Test locally (make dev)
   └─ Create pull request

2. Pre-Deployment
   ├─ ./scripts/pre-deploy-check.sh
   ├─ Fix any issues
   └─ Commit changes

3. Deployment
   ├─ ./scripts/deploy-production.sh
   ├─ Monitor logs
   └─ Wait for completion

4. Verification
   ├─ ./scripts/health-check.sh
   ├─ Test end-to-end
   └─ Monitor for 30 minutes

5. Post-Deployment
   ├─ Update documentation
   ├─ Notify team
   └─ Monitor metrics

If Issues:
   └─ ./scripts/rollback.sh
```

---

*Last updated: October 15, 2025*
