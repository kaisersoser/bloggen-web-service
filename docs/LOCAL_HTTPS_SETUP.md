# Local HTTPS Development Setup Guide

## 🔒 Why HTTPS in Development?

Your application now enforces HTTPS in **all environments** for maximum security:
- **Consistent Environment**: Same security in development as production
- **Early Detection**: Catch HTTPS-related issues during development
- **Authentication Security**: JWT tokens always encrypted
- **WebSocket Security**: WSS (WebSocket Secure) connections

## 🚀 Quick Setup (Automated)

### 1. Run the Setup Script
```bash
cd frontend-nextjs/blog-generator-ui
./setup-local-https.sh
```

This script will:
- Install `mkcert` (if not installed)
- Create local Certificate Authority
- Generate HTTPS certificates for localhost
- Configure Next.js for HTTPS
- Update package.json scripts

### 2. Start Your Servers
```bash
# Terminal 1: Start Frontend with HTTPS
cd frontend-nextjs/blog-generator-ui
npm run dev:https
# or: node dev-https.js

# Terminal 2: Start Backend with HTTPS
cd backend
python src/main.py
```

### 3. Access Your Application
- **Frontend**: https://localhost:3001
- **Backend**: https://localhost:5000 (if certificates are shared)
- **WebSockets**: Automatically use WSS

## 🛠️ Manual Setup

### Step 1: Install mkcert

#### macOS
```bash
brew install mkcert
brew install nss # if you use Firefox
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt install libnss3-tools
curl -JLO "https://dl.filippo.io/mkcert/latest?for=linux/amd64"
chmod +x mkcert-v*-linux-amd64
sudo mv mkcert-v*-linux-amd64 /usr/local/bin/mkcert
```

#### Windows
1. Download from: https://github.com/FiloSottile/mkcert/releases
2. Extract to a directory in your PATH

### Step 2: Install Local Certificate Authority
```bash
mkcert -install
```

This installs a local CA that your browser will trust.

### Step 3: Generate Certificates
```bash
# Create certificates directory
mkdir -p frontend-nextjs/blog-generator-ui/certs
cd frontend-nextjs/blog-generator-ui/certs

# Generate certificates for localhost
mkcert localhost 127.0.0.1 ::1

# Rename for easier reference
mv localhost+2.pem localhost.pem
mv localhost+2-key.pem localhost-key.pem
```

### Step 4: Configure Frontend

#### Update next.config.ts
```typescript
import { NextConfig } from 'next'
import fs from 'fs'
import path from 'path'

const nextConfig: NextConfig = {
  experimental: {
    serverComponentsExternalPackages: ['@prisma/client'],
  }
}

export default nextConfig
```

#### Create HTTPS Development Server
Create `dev-https.js`:
```javascript
const { createServer } = require('https')
const { parse } = require('url')
const next = require('next')
const fs = require('fs')
const path = require('path')

const dev = process.env.NODE_ENV !== 'production'
const app = next({ dev })
const handle = app.getRequestHandler()

const httpsOptions = {
  key: fs.readFileSync(path.join(__dirname, 'certs', 'localhost-key.pem')),
  cert: fs.readFileSync(path.join(__dirname, 'certs', 'localhost.pem')),
}

app.prepare().then(() => {
  createServer(httpsOptions, (req, res) => {
    const parsedUrl = parse(req.url, true)
    handle(req, res, parsedUrl)
  }).listen(3001, (err) => {
    if (err) throw err
    console.log('🔒 HTTPS Server ready on https://localhost:3001')
  })
})
```

#### Update package.json
```json
{
  "scripts": {
    "dev:https": "node dev-https.js"
  }
}
```

### Step 5: Backend HTTPS (Optional)

The backend will automatically detect and use the frontend certificates if available. If you want dedicated backend certificates:

```bash
# Copy certificates for backend
mkdir -p backend/src/certs
cp frontend-nextjs/blog-generator-ui/certs/localhost.pem backend/src/certs/
cp frontend-nextjs/blog-generator-ui/certs/localhost-key.pem backend/src/certs/
```

## 🔧 Configuration Files

### Frontend Environment (.env.local)
```bash
# HTTPS required in development
NEXTAUTH_URL=https://localhost:3001
API_BASE_URL=https://localhost:5000
NEXT_PUBLIC_API_URL=https://localhost:5000
```

### Backend Environment (.env)
```bash
# HTTPS required in development
ENVIRONMENT=development
FRONTEND_URL=https://localhost:3001
NEXTAUTH_URL=https://localhost:3001
API_URL=https://localhost:5000
```

## 🌐 Browser Considerations

### First Time Setup
When you first access https://localhost:3001, your browser may show:
- ⚠️ "Your connection is not private"
- ⚠️ "Advanced" → "Proceed to localhost (unsafe)"

This is normal for self-signed certificates. Click "Advanced" and proceed.

### Trusted Certificates
After running `mkcert -install`, certificates will be automatically trusted in:
- ✅ Chrome/Chromium
- ✅ Edge
- ✅ Safari (macOS)
- ✅ Firefox (if you installed NSS tools)

## 🚨 Troubleshooting

### Certificate Not Trusted
```bash
# Reinstall the local CA
mkcert -uninstall
mkcert -install
```

### Port Already in Use
```bash
# Kill processes on ports
sudo lsof -ti:3001 | xargs kill -9
sudo lsof -ti:5000 | xargs kill -9
```

### Certificate File Not Found
```bash
# Regenerate certificates
cd frontend-nextjs/blog-generator-ui/certs
mkcert localhost 127.0.0.1 ::1
mv localhost+2.pem localhost.pem
mv localhost+2-key.pem localhost-key.pem
```

### WebSocket Connection Issues
- Ensure NEXT_PUBLIC_API_URL uses https://
- Check that backend accepts WSS connections
- Verify firewall allows HTTPS traffic

## 📝 Testing Your Setup

### 1. Test Frontend HTTPS
```bash
curl -k https://localhost:3001
```

### 2. Test Backend HTTPS
```bash
curl -k https://localhost:5000/health
```

### 3. Test Authentication
```bash
# Should require HTTPS
curl -X POST https://localhost:5000/generate-blog \
     -H "Content-Type: application/json" \
     -d '{"topic": "Test"}'
```

## 🔄 Development Workflow

1. **Start Session**:
   ```bash
   # Terminal 1: Frontend
   cd frontend-nextjs/blog-generator-ui
   npm run dev:https
   
   # Terminal 2: Backend
   cd backend
   python src/main.py
   ```

2. **Access Application**:
   - Frontend: https://localhost:3001
   - Backend API: https://localhost:5000

3. **Development as Usual**:
   - Hot reload works normally
   - All requests use HTTPS
   - WebSockets use WSS

## 🎯 Benefits

- **Security First**: Same security model in dev and prod
- **Early Detection**: Catch HTTPS issues before deployment
- **Realistic Testing**: Test with real WSS connections
- **Authentication**: JWT tokens always encrypted
- **Browser APIs**: Access HTTPS-only browser features

Your development environment is now as secure as production! 🔒
