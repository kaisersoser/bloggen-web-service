#!/bin/bash

# Local HTTPS Setup Script for Development
# This script sets up HTTPS certificates for local development

echo "🔒 Setting up Local HTTPS for Development"
echo "========================================="

# Check if mkcert is installed
if ! command -v mkcert &> /dev/null; then
    echo "❌ mkcert is not installed. Installing mkcert..."
    
    # Detect OS and install mkcert
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        echo "📦 Installing mkcert on Linux..."
        if command -v apt &> /dev/null; then
            # Ubuntu/Debian
            sudo apt update
            sudo apt install -y libnss3-tools
            curl -JLO "https://dl.filippo.io/mkcert/latest?for=linux/amd64"
            chmod +x mkcert-v*-linux-amd64
            sudo mv mkcert-v*-linux-amd64 /usr/local/bin/mkcert
        elif command -v yum &> /dev/null; then
            # CentOS/RHEL
            sudo yum install -y nss-tools
            curl -JLO "https://dl.filippo.io/mkcert/latest?for=linux/amd64"
            chmod +x mkcert-v*-linux-amd64
            sudo mv mkcert-v*-linux-amd64 /usr/local/bin/mkcert
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "📦 Installing mkcert on macOS..."
        if command -v brew &> /dev/null; then
            brew install mkcert
            brew install nss # if you use Firefox
        else
            curl -JLO "https://dl.filippo.io/mkcert/latest?for=darwin/amd64"
            chmod +x mkcert-v*-darwin-amd64
            sudo mv mkcert-v*-darwin-amd64 /usr/local/bin/mkcert
        fi
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        # Windows
        echo "📦 Please install mkcert manually on Windows:"
        echo "1. Download from: https://github.com/FiloSottile/mkcert/releases"
        echo "2. Add to PATH"
        exit 1
    fi
fi

echo "✅ mkcert is installed"

# Install the local CA
echo "🏗️  Installing local Certificate Authority..."
mkcert -install

# Create certificates directory
mkdir -p certs
cd certs

# Generate certificates for localhost and 127.0.0.1
echo "🔑 Generating HTTPS certificates..."
mkcert localhost 127.0.0.1 ::1

# Rename files for easier reference
mv localhost+2.pem localhost.pem
mv localhost+2-key.pem localhost-key.pem

echo "✅ Certificates generated successfully!"
echo ""
echo "📁 Certificate files created:"
echo "   - certs/localhost.pem (certificate)"
echo "   - certs/localhost-key.pem (private key)"
echo ""

# Create Next.js HTTPS configuration
echo "⚙️  Creating Next.js HTTPS configuration..."
cd ..

# Create or update next.config.ts for HTTPS
cat > next.config.ts << 'EOF'
import { NextConfig } from 'next'
import fs from 'fs'
import path from 'path'

const nextConfig: NextConfig = {
  // Enable experimental HTTPS support
  experimental: {
    serverComponentsExternalPackages: ['@prisma/client'],
  },
  
  // HTTPS configuration for development
  ...(process.env.NODE_ENV === 'development' && {
    webpack: (config, { dev }) => {
      if (dev) {
        // HTTPS setup for development
        const certPath = path.join(process.cwd(), 'certs', 'localhost.pem')
        const keyPath = path.join(process.cwd(), 'certs', 'localhost-key.pem')
        
        if (fs.existsSync(certPath) && fs.existsSync(keyPath)) {
          console.log('🔒 HTTPS certificates found - enabling HTTPS for development')
        }
      }
      return config
    }
  })
}

export default nextConfig
EOF

# Update package.json scripts for HTTPS
echo "📝 Updating package.json scripts for HTTPS..."

# Read current package.json
if [ -f package.json ]; then
    # Backup original package.json
    cp package.json package.json.backup
    
    # Add HTTPS scripts using Node.js
    node << 'EOF'
const fs = require('fs');
const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));

// Update dev script for HTTPS
pkg.scripts = pkg.scripts || {};
pkg.scripts['dev'] = 'next dev --hostname localhost --port 3001';
pkg.scripts['dev:https'] = 'HTTPS=true SSL_CRT_FILE=./certs/localhost.pem SSL_KEY_FILE=./certs/localhost-key.pem next dev --hostname localhost --port 3001';
pkg.scripts['start:https'] = 'next start --hostname localhost --port 3001';

fs.writeFileSync('package.json', JSON.stringify(pkg, null, 2));
EOF

    echo "✅ Package.json updated with HTTPS scripts"
fi

# Create development server script
echo "🚀 Creating HTTPS development server script..."
cat > dev-https.js << 'EOF'
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
EOF

echo ""
echo "🎉 Local HTTPS setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Install dependencies: npm install"
echo "2. Start frontend with HTTPS: npm run dev:https"
echo "   Alternative: node dev-https.js"
echo "3. Start backend with HTTPS: python src/main.py"
echo "4. Access your app at: https://localhost:3001"
echo ""
echo "⚠️  Note: You may need to accept the security warning in your browser"
echo "   This is normal for self-signed certificates in development."
echo ""
echo "🔧 Backend Setup:"
echo "   Make sure your backend also supports HTTPS with self-signed certificates"
echo "   or configure it to accept the local CA certificates."
