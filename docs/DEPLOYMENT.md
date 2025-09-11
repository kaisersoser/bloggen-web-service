# Deployment Configuration Guide

## 🚀 Dynamic URL Configuration

The backend is now configured to handle multiple deployment scenarios automatically.

## Environment Variables for Deployment

### Development (Local)
```bash
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3001
NEXTAUTH_URL=http://localhost:3001
NEXTAUTH_SECRET=your-development-secret-here
```

### Production (Deployed) - HTTPS REQUIRED
```bash
ENVIRONMENT=production
FRONTEND_URL=https://your-app.vercel.app      # HTTPS required
NEXTAUTH_URL=https://your-app.vercel.app      # HTTPS required
NEXTAUTH_SECRET=your-production-secret        # Different from dev
PRODUCTION_DOMAINS=https://your-app.vercel.app,https://www.yourdomain.com,https://custom-domain.com
```

⚠️ **Security Note**: All production URLs MUST use HTTPS. HTTP requests will be rejected with 426 Upgrade Required.

## Common Deployment Platforms

### 1. Railway
```bash
# Set environment variables in Railway dashboard
ENVIRONMENT=production
FRONTEND_URL=https://your-app.up.railway.app  # HTTPS required
PRODUCTION_DOMAINS=https://your-app.up.railway.app
```

### 2. Render
```bash
# Set environment variables in Render dashboard
ENVIRONMENT=production
FRONTEND_URL=https://your-app.onrender.com    # HTTPS required
PRODUCTION_DOMAINS=https://your-app.onrender.com
```

### 3. Heroku
```bash
# Set environment variables with Heroku CLI
heroku config:set ENVIRONMENT=production
heroku config:set FRONTEND_URL=https://your-app.herokuapp.com  # HTTPS required
heroku config:set PRODUCTION_DOMAINS=https://your-app.herokuapp.com
```

### 4. DigitalOcean App Platform
```bash
# Set in DigitalOcean dashboard
ENVIRONMENT=production
FRONTEND_URL=https://your-app-12345.ondigitalocean.app  # HTTPS required
PRODUCTION_DOMAINS=https://your-app-12345.ondigitalocean.app
```

## Frontend Deployment (Vercel/Netlify)

### Vercel
```bash
# .env.local for Vercel
NEXTAUTH_URL=https://your-app.vercel.app
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
```

### Netlify
```bash
# .env.local for Netlify
NEXTAUTH_URL=https://your-app.netlify.app
NEXT_PUBLIC_API_URL=https://your-backend.render.com
```

## Full Stack Deployment Examples

### Example 1: Frontend on Vercel, Backend on Railway
```bash
# Frontend (.env.local)
NEXTAUTH_URL=https://your-app.vercel.app
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app

# Backend (.env)
ENVIRONMENT=production
FRONTEND_URL=https://your-app.vercel.app
PRODUCTION_DOMAINS=https://your-app.vercel.app
```

### Example 2: Frontend on Netlify, Backend on Render
```bash
# Frontend (.env.local)
NEXTAUTH_URL=https://your-app.netlify.app
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com

# Backend (.env)
ENVIRONMENT=production
FRONTEND_URL=https://your-app.netlify.app
PRODUCTION_DOMAINS=https://your-app.netlify.app
```

## Custom Domain Setup

### With Custom Domain
```bash
# Frontend (.env.local)
NEXTAUTH_URL=https://blog.yourdomain.com
NEXT_PUBLIC_API_URL=https://api.yourdomain.com

# Backend (.env)
ENVIRONMENT=production
FRONTEND_URL=https://blog.yourdomain.com
PRODUCTION_DOMAINS=https://blog.yourdomain.com,https://www.yourdomain.com
```

## Security Considerations

### 1. Environment-Specific CORS
- **Development**: Allows localhost origins
- **Production**: Only allows specified domains
- **Staging**: Flexible for testing

### 2. Secret Management
- Use different `NEXTAUTH_SECRET` for each environment
- Store secrets securely in platform-specific secret managers
- Never commit secrets to version control

### 3. Domain Validation
- Only add legitimate domains to `PRODUCTION_DOMAINS`
- Validate all URLs are HTTPS in production
- Use environment variables, not hardcoded values

## Testing Your Deployment

### 1. Check CORS Origins
```bash
# Should return your app's URL
curl -H "Origin: https://your-app.vercel.app" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS https://your-backend.railway.app/generate-blog
```

### 2. Test Authentication
```bash
# Should require authentication
curl -X POST https://your-backend.railway.app/generate-blog \
     -H "Content-Type: application/json" \
     -d '{"topic": "Test"}'
```

### 3. Check Environment
```bash
# Add a debug endpoint to verify configuration
curl https://your-backend.railway.app/debug/config
```

## Deployment Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Configure `FRONTEND_URL` with deployed frontend URL (HTTPS required)
- [ ] Set `PRODUCTION_DOMAINS` with all allowed domains (HTTPS required)
- [ ] Update `NEXTAUTH_URL` to match frontend URL (HTTPS required)
- [ ] Use production-grade `NEXTAUTH_SECRET`
- [ ] Configure database connection for production (set identical `DATABASE_URL` in frontend and backend env files)
- [ ] Set up proper logging
- [ ] **Verify all URLs use HTTPS (HTTP will be rejected)**
- [ ] Test HTTPS enforcement
- [ ] Verify security headers are present
- [ ] Test CORS configuration
- [ ] Verify authentication flow works over HTTPS
- [ ] Test WebSocket connections use WSS (not WS)

## Troubleshooting

### CORS Issues
- Check that `FRONTEND_URL` matches your deployed frontend exactly
- Ensure `PRODUCTION_DOMAINS` includes all necessary domains
- Verify environment variables are set correctly

### Authentication Issues
- Confirm `NEXTAUTH_SECRET` is the same in frontend and backend
- Check that `NEXTAUTH_URL` matches your frontend URL
- Ensure JWT tokens are being passed correctly

### Environment Detection
- Set `ENVIRONMENT=production` explicitly
- Check logs for "Environment: production" message
- Verify CORS origins list in startup logs
