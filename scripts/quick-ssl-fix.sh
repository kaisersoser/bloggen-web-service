#!/bin/bash

# Immediate SSL Certificate Fix
# Quick solution for current development session

echo "🚀 Quick SSL Certificate Fix"
echo "============================"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="$PROJECT_ROOT/certs"

# Regenerate certificates with enhanced configuration
echo "📋 Regenerating SSL certificates..."

# Enhanced configuration with all possible hostnames
cat > "$CERTS_DIR/localhost.conf" << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=US
ST=Development
L=Local
O=BlogGen Development
OU=Development
CN=localhost

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.localhost
DNS.3 = 127.0.0.1
DNS.4 = ::1
DNS.5 = $(hostname)
DNS.6 = $(hostname).local
IP.1 = 127.0.0.1
IP.2 = ::1
IP.3 = $(hostname -I | awk '{print $1}')
EOF

# Backup existing certificates
if [ -f "$CERTS_DIR/localhost.pem" ]; then
    cp "$CERTS_DIR/localhost.pem" "$CERTS_DIR/localhost.pem.backup.$(date +%Y%m%d_%H%M%S)"
fi
if [ -f "$CERTS_DIR/localhost-key.pem" ]; then
    cp "$CERTS_DIR/localhost-key.pem" "$CERTS_DIR/localhost-key.pem.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Generate new private key
openssl genpkey -algorithm RSA -out "$CERTS_DIR/localhost-key.pem" -pkcs8 2>/dev/null

# Generate new self-signed certificate (valid for 1 year)
openssl req -new -x509 -config "$CERTS_DIR/localhost.conf" -key "$CERTS_DIR/localhost-key.pem" -out "$CERTS_DIR/localhost.pem" -days 365 -extensions v3_req

# Copy to frontend certs directory
mkdir -p "$PROJECT_ROOT/frontend-nextjs/blog-generator-ui/certs"
cp "$CERTS_DIR/localhost.pem" "$PROJECT_ROOT/frontend-nextjs/blog-generator-ui/certs/"
cp "$CERTS_DIR/localhost-key.pem" "$PROJECT_ROOT/frontend-nextjs/blog-generator-ui/certs/"

echo "✅ SSL certificates regenerated"

# Set environment variable for Node.js to accept self-signed certificates
export NODE_TLS_REJECT_UNAUTHORIZED=0

echo "✅ Node.js configured to accept self-signed certificates"

# Update development scripts
cat > "$PROJECT_ROOT/frontend-nextjs/blog-generator-ui/dev-secure.js" << 'EOF'
// Secure development server with SSL bypass
process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

const { createServer } = require('https');
const { parse } = require('url');
const next = require('next');
const fs = require('fs');
const path = require('path');

const dev = process.env.NODE_ENV !== 'production';
const hostname = 'localhost';
const port = 3001;

const app = next({ dev, hostname, port });
const handle = app.getRequestHandler();

// SSL certificate paths
const certPath = path.join(__dirname, 'certs', 'localhost.pem');
const keyPath = path.join(__dirname, 'certs', 'localhost-key.pem');

console.log('🔧 Starting secure development server...');
console.log('🔒 SSL certificates:', { certPath, keyPath });
console.log('⚠️  SSL verification disabled for development');

app.prepare().then(() => {
  const httpsOptions = {
    key: fs.readFileSync(keyPath),
    cert: fs.readFileSync(certPath)
  };

  createServer(httpsOptions, async (req, res) => {
    const parsedUrl = parse(req.url, true);
    await handle(req, res, parsedUrl);
  }).listen(port, (err) => {
    if (err) throw err;
    console.log(`🚀 HTTPS Server ready on https://${hostname}:${port}`);
    console.log('🌐 To fix browser warnings:');
    console.log('   1. Visit https://localhost:3001 in your browser');
    console.log('   2. Click "Advanced" when you see the security warning');
    console.log('   3. Click "Proceed to localhost (unsafe)"');
    console.log('   4. Your browser will remember this choice for this session');
  });
});
EOF

echo "✅ Secure development server script created"

# Create quick-start script
cat > "$PROJECT_ROOT/quick-start-ssl.sh" << 'EOF'
#!/bin/bash

echo "🚀 Quick Start with SSL Fix"
echo "=========================="

# Set environment variables
export NODE_TLS_REJECT_UNAUTHORIZED=0

# Start backend
echo "📋 Starting backend..."
cd backend && source .venv/bin/activate && python src/main.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
echo "📋 Starting frontend..."
cd ../frontend-nextjs/blog-generator-ui && node dev-secure.js &
FRONTEND_PID=$!

echo ""
echo "🎉 Services starting..."
echo "Backend: https://localhost:5000"
echo "Frontend: https://localhost:3001"
echo ""
echo "⚠️  Browser SSL Warning Fix:"
echo "1. Visit https://localhost:3001"
echo "2. Click 'Advanced' → 'Proceed to localhost (unsafe)'"
echo "3. Application will load normally"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
EOF

chmod +x "$PROJECT_ROOT/quick-start-ssl.sh"

echo "✅ Quick start script created"

echo ""
echo "🎉 IMMEDIATE SSL FIX COMPLETE!"
echo "============================="
echo ""
echo "📋 Quick Start Options:"
echo "  Option 1 - Use quick start script:"
echo "    ./quick-start-ssl.sh"
echo ""
echo "  Option 2 - Manual start:"
echo "    Backend: cd backend && source .venv/bin/activate && python src/main.py"
echo "    Frontend: cd frontend-nextjs/blog-generator-ui && node dev-secure.js"
echo ""
echo "📋 Browser Instructions:"
echo "  1. Visit https://localhost:3001"
echo "  2. Click 'Advanced' when you see SSL warning"
echo "  3. Click 'Proceed to localhost (unsafe)'"
echo "  4. Application will work normally"
echo ""
echo "📋 For permanent fix:"
echo "  Run: ./setup-ssl-ca.sh (creates proper Certificate Authority)"
