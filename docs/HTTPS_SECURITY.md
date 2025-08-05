# HTTPS Security Configuration

## 🔒 HTTPS-Only Communication

The backend and frontend are now configured to enforce HTTPS-only communication in **ALL environments** (development and production) for maximum security.

## Security Features

### 🛡️ HTTPS Enforcement
- **All Environments**: All HTTP requests are rejected with 426 Upgrade Required
- **Development**: HTTPS required even on localhost (using self-signed certificates)
- **Production**: HTTPS required for all domains
- **Automatic URL Conversion**: HTTP URLs are automatically converted to HTTPS in logs

### 🔐 Security Headers
When running in any environment, the following security headers are automatically added:

#### Strict Transport Security (HSTS)
**Production:**
```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

**Development:**
```
Strict-Transport-Security: max-age=3600; includeSubDomains
```
- Forces browsers to use HTTPS
- Production: Forces HTTPS for 1 year with preload
- Development: Forces HTTPS for 1 hour

#### Content Security Policy (CSP)
**Production:**
```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; ...
```

**Development:**
```
Content-Security-Policy: default-src 'self' https://localhost:* https://127.0.0.1:*; ...
```
- Prevents XSS attacks
- Restricts resource loading to trusted sources
- Development: Allows localhost HTTPS connections

#### Additional Security Headers
- `X-Frame-Options: DENY` - Prevents clickjacking
- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `X-XSS-Protection: 1; mode=block` - Enables XSS protection
- `Referrer-Policy: strict-origin-when-cross-origin` - Controls referrer information
- `Permissions-Policy` - Disables unnecessary browser features

## Environment Configuration

### Development Environment (HTTPS Required)
```bash
ENVIRONMENT=development
FRONTEND_URL=https://localhost:3001  # HTTPS required
API_BASE_URL=https://localhost:5000  # HTTPS required
NEXT_PUBLIC_API_URL=https://localhost:5000  # WebSocket (WSS)
```

### Production Environment (HTTPS Required)
```bash
ENVIRONMENT=production
FRONTEND_URL=https://your-app.vercel.app     # HTTPS required
API_BASE_URL=https://your-backend.railway.app # HTTPS required
PRODUCTION_DOMAINS=https://your-app.vercel.app,https://custom-domain.com
```

⚠️ **Important**: HTTPS is now required in ALL environments, including development.

## Local HTTPS Development Setup

Since HTTPS is now required in development, you need to set up local HTTPS certificates:

### Automatic Setup (Recommended)
```bash
# Run the setup script
cd frontend-nextjs/blog-generator-ui
./setup-local-https.sh
```

### Manual Setup
1. **Install mkcert**:
   ```bash
   # macOS
   brew install mkcert
   
   # Linux
   sudo apt install libnss3-tools
   curl -JLO "https://dl.filippo.io/mkcert/latest?for=linux/amd64"
   chmod +x mkcert-v*-linux-amd64
   sudo mv mkcert-v*-linux-amd64 /usr/local/bin/mkcert
   ```

2. **Install local CA**:
   ```bash
   mkcert -install
   ```

3. **Generate certificates**:
   ```bash
   mkdir certs
   cd certs
   mkcert localhost 127.0.0.1 ::1
   mv localhost+2.pem localhost.pem
   mv localhost+2-key.pem localhost-key.pem
   ```

4. **Start with HTTPS**:
   ```bash
   # Frontend
   npm run dev:https
   # or
   node dev-https.js
   
   # Backend
   python src/main.py
   ```

### Accessing Your App
- **Frontend**: https://localhost:3001
- **Backend**: https://localhost:5000
- **Accept Security Warning**: Normal for self-signed certificates

## Deployment Platform Configuration

### 1. Vercel (Frontend)
```bash
# Vercel automatically provides HTTPS
NEXTAUTH_URL=https://your-app.vercel.app
API_BASE_URL=https://your-backend.railway.app
```

### 2. Railway (Backend)
```bash
# Railway automatically provides HTTPS
ENVIRONMENT=production
FRONTEND_URL=https://your-app.vercel.app
PRODUCTION_DOMAINS=https://your-app.vercel.app
```

### 3. Render (Backend)
```bash
# Render automatically provides HTTPS
ENVIRONMENT=production
FRONTEND_URL=https://your-app.vercel.app
PRODUCTION_DOMAINS=https://your-app.vercel.app
```

### 4. Custom Domain Setup
```bash
# Frontend
NEXTAUTH_URL=https://blog.yourdomain.com

# Backend
ENVIRONMENT=production
FRONTEND_URL=https://blog.yourdomain.com
PRODUCTION_DOMAINS=https://blog.yourdomain.com,https://www.yourdomain.com
```

## Security Benefits

### 🔐 Encryption
- All data in transit is encrypted with TLS/SSL
- Prevents man-in-the-middle attacks
- Protects authentication tokens and sensitive data

### 🛡️ Authentication Protection
- JWT tokens are transmitted securely over HTTPS
- Session cookies are marked as secure
- Prevents token interception

### 🚫 Attack Prevention
- HSTS prevents downgrade attacks
- CSP prevents XSS attacks
- Security headers prevent various web vulnerabilities

## Health Check Endpoints

Special endpoints that can be accessed without HTTPS enforcement (for load balancers):

```bash
GET /health  # Health check with security status
GET /ping    # Simple ping endpoint
```

Example response:
```json
{
  "status": "healthy",
  "timestamp": "2025-07-19T12:00:00Z",
  "environment": "production",
  "https_enforced": true
}
```

## Testing HTTPS Configuration

### 1. Test HTTP Rejection (Production)
```bash
# Should return 426 Upgrade Required
curl -X POST http://your-backend.railway.app/generate-blog \
     -H "Content-Type: application/json" \
     -d '{"topic": "Test"}'
```

### 2. Test HTTPS Success (Production)
```bash
# Should work with valid authentication
curl -X POST https://your-backend.railway.app/generate-blog \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{"topic": "Test"}'
```

### 3. Test Security Headers
```bash
# Check security headers
curl -I https://your-backend.railway.app/health
```

## SSL/TLS Certificate Requirements

### Deployment Platforms
- **Vercel**: Automatic SSL certificates
- **Railway**: Automatic SSL certificates
- **Render**: Automatic SSL certificates
- **Netlify**: Automatic SSL certificates

### Custom Domains
- Use Let's Encrypt for free SSL certificates
- Configure DNS properly for certificate validation
- Ensure certificates are automatically renewed

## Troubleshooting

### Common Issues

#### 1. Mixed Content Warnings
- Ensure all resources (images, scripts, APIs) use HTTPS
- Check browser console for mixed content errors

#### 2. CORS Issues with HTTPS
- Verify all origins in CORS configuration use HTTPS
- Check that FRONTEND_URL matches exactly

#### 3. Certificate Issues
- Verify SSL certificate is valid and not expired
- Check certificate chain is complete

#### 4. Load Balancer Configuration
- Ensure load balancer terminates SSL properly
- Configure X-Forwarded-Proto header correctly

## Migration from HTTP to HTTPS

### Step 1: Update Environment Variables
```bash
# Change all HTTP URLs to HTTPS
FRONTEND_URL=https://your-app.vercel.app
API_BASE_URL=https://your-backend.railway.app
```

### Step 2: Deploy with HTTPS
```bash
# Set environment to production
ENVIRONMENT=production
```

### Step 3: Test All Endpoints
- Verify authentication works over HTTPS
- Test WebSocket connections (WSS)
- Check all API endpoints

### Step 4: Monitor Security Headers
```bash
# Use security header checkers
curl -I https://your-backend.railway.app/health
```

## Best Practices

1. **Always use HTTPS in production**
2. **Keep certificates up to date**
3. **Monitor security headers**
4. **Test HTTPS configuration regularly**
5. **Use HSTS preload list for public sites**
6. **Implement proper certificate pinning for mobile apps**

## Security Compliance

This configuration helps meet various security standards:
- **OWASP Top 10** protection
- **PCI DSS** compliance for payment processing
- **GDPR** data protection requirements
- **SOC 2** security controls
