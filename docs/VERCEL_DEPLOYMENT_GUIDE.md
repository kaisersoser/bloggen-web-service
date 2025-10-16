# Frontend Deployment to Vercel - Configuration Guide

## 🎯 Prerequisites

✅ Railway backend is deployed and running
✅ You have your Railway backend URL

## 🔍 Step 1: Get Your Railway Backend URL

### Option A: Railway Dashboard
1. Go to https://railway.app/dashboard
2. Click your project → Your service
3. Look for **Domains** section
4. Copy the public URL (e.g., `https://bloggen-web-service-production.up.railway.app`)

### Option B: Railway CLI
```bash
railway status
```

### Option C: From Deployment Logs
The URL appears at the top of successful deployment details.

---

## 🚀 Step 2: Deploy Frontend to Vercel

### A. Connect Repository to Vercel

1. Go to https://vercel.com/dashboard
2. Click **"Add New..." → Project**
3. Import your Git repository: `kaisersoser/bloggen-web-service`
4. Select the **frontend directory**: `frontend-nextjs/blog-generator-ui`
5. Click **"Deploy"** (it will fail first time - that's ok, we need to add env vars)

### B. Configure Environment Variables

In Vercel Dashboard → Your Project → **Settings** → **Environment Variables**

Add these variables for **Production, Preview, and Development**:

```bash
# ============================================
# BACKEND API CONNECTION
# ============================================
NEXT_PUBLIC_API_URL=https://YOUR-RAILWAY-URL.railway.app
# Replace with your actual Railway URL from Step 1

# ============================================
# NEXTAUTH CONFIGURATION
# ============================================
NEXTAUTH_URL=https://YOUR-VERCEL-APP.vercel.app
# This will be provided by Vercel after first deployment
# For now, use: https://your-app-name.vercel.app

NEXTAUTH_SECRET=your-nextauth-secret-here
# IMPORTANT: Use the SAME value as in Railway backend

JWT_SECRET=your-jwt-secret-here
# IMPORTANT: Must match Railway backend JWT_SECRET

# ============================================
# DATABASE (Supabase)
# ============================================
DATABASE_URL=postgresql://postgres.PROJECT_REF::PASSWORD@aws-0-eu-west-3.pooler.supabase.com:5432/postgres
# Use EXACT same connection string as Railway backend
# Remember: port 5432, not 6543!

# ============================================
# OAUTH PROVIDERS
# ============================================
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret

GITHUB_ID=your-github-oauth-app-id
GITHUB_SECRET=your-github-oauth-app-secret

# ============================================
# OPTIONAL: REDIS (if frontend uses it)
# ============================================
# REDIS_URL=rediss://default:PASSWORD@eternal-duck-8525.upstash.io:6379
```

---

## 🔐 Step 3: Update OAuth Callback URLs

### Google OAuth Console
1. Go to https://console.cloud.google.com/apis/credentials
2. Edit your OAuth 2.0 Client ID
3. Add authorized redirect URIs:
   ```
   https://your-vercel-app.vercel.app/api/auth/callback/google
   https://your-railway-url.railway.app/api/auth/callback/google
   ```

### GitHub OAuth App
1. Go to https://github.com/settings/developers
2. Click your OAuth App
3. Update **Authorization callback URL**:
   ```
   https://your-vercel-app.vercel.app/api/auth/callback/github
   ```

---

## ✅ Step 4: Verify Environment Variables

### Required Variables Checklist

- [ ] `NEXT_PUBLIC_API_URL` - Points to Railway backend
- [ ] `NEXTAUTH_URL` - Your Vercel app URL
- [ ] `NEXTAUTH_SECRET` - Matches backend
- [ ] `JWT_SECRET` - Matches backend
- [ ] `DATABASE_URL` - Same as backend (port 5432!)
- [ ] `GOOGLE_CLIENT_ID` - OAuth credentials
- [ ] `GOOGLE_CLIENT_SECRET` - OAuth credentials
- [ ] `GITHUB_ID` - OAuth credentials
- [ ] `GITHUB_SECRET` - OAuth credentials

---

## 🚀 Step 5: Redeploy Frontend

After adding all environment variables:

1. Go to **Deployments** tab in Vercel
2. Click **"Redeploy"** on the latest deployment
3. Or push a new commit to trigger auto-deployment

---

## 🧪 Step 6: Test the Deployment

### Test Backend Connection
```bash
# Replace with your Vercel URL
curl https://your-app.vercel.app/api/health

# Should proxy to Railway backend and return:
{
  "status": "healthy",
  "timestamp": "...",
  "services": {
    "database": "connected",
    "redis": "connected"
  }
}
```

### Test Frontend
1. Visit https://your-app.vercel.app
2. Try logging in with Google/GitHub
3. Test blog generation

---

## 🔧 Troubleshooting

### Issue: "Failed to fetch" errors
**Cause**: CORS issue between Vercel frontend and Railway backend
**Fix**: Update Railway backend CORS settings to allow Vercel domain

### Issue: OAuth redirect errors
**Cause**: Callback URLs not configured
**Fix**: Add Vercel URLs to Google/GitHub OAuth settings

### Issue: Database connection errors
**Cause**: Wrong DATABASE_URL or port
**Fix**: Ensure using port 5432, not 6543

### Issue: "Invalid token" errors
**Cause**: JWT_SECRET mismatch between frontend and backend
**Fix**: Ensure EXACT same JWT_SECRET in both Vercel and Railway

---

## 📋 Quick Reference

### Your Deployment URLs

**Backend (Railway):**
```
https://YOUR-RAILWAY-URL.railway.app
```

**Frontend (Vercel):**
```
https://YOUR-APP-NAME.vercel.app
```

**Health Check:**
```
Backend: https://YOUR-RAILWAY-URL.railway.app/health
Frontend: https://YOUR-APP-NAME.vercel.app
```

---

## 🎉 Success Criteria

✅ Vercel deployment shows "Ready" status
✅ Frontend loads without errors
✅ OAuth login works (Google/GitHub)
✅ Can create new blog
✅ SSE streaming shows real-time progress
✅ Database operations work

---

## 📚 Next Steps After Deployment

1. **Update CORS** in Railway backend to allow Vercel domain
2. **Test all features** thoroughly
3. **Monitor logs** in both Vercel and Railway
4. **Set up custom domain** (optional)
5. **Enable analytics** (Vercel Analytics)
6. **Set up monitoring** (error tracking with Sentry)

---

**Last Updated**: October 17, 2025
**Backend Status**: ✅ Deployed on Railway
**Frontend Status**: ⏳ Ready to deploy on Vercel
