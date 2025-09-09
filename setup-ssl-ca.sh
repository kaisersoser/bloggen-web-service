#!/bin/bash

# Comprehensive SSL Certificate Setup Script
# Provides permanent solution for certificate authority issues in development

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="$PROJECT_ROOT/certs"
FRONTEND_CERTS_DIR="$PROJECT_ROOT/frontend-nextjs/blog-generator-ui/certs"

echo "🔒 BlogGen SSL Certificate Setup - Permanent CA Solution"
echo "======================================================"

# Create directories
mkdir -p "$CERTS_DIR"
mkdir -p "$FRONTEND_CERTS_DIR"

# Step 1: Create a local Certificate Authority (CA)
echo "📋 Step 1: Creating Local Certificate Authority..."

# Generate CA private key
openssl genpkey -algorithm RSA -out "$CERTS_DIR/bloggen-ca-key.pem" -pkcs8 -aes256 -pass pass:bloggen-dev-ca 2>/dev/null

# Create CA certificate
cat > "$CERTS_DIR/bloggen-ca.conf" << EOF
[req]
default_bits = 4096
prompt = no
default_md = sha256
distinguished_name = dn
x509_extensions = v3_ca

[dn]
C=US
ST=Development
L=Local
O=BlogGen Development CA
OU=Certificate Authority
CN=BlogGen Development Root CA

[v3_ca]
basicConstraints = critical, CA:true
keyUsage = critical, digitalSignature, cRLSign, keyCertSign
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer:always
EOF

# Generate CA certificate (valid for 10 years)
openssl req -new -x509 -config "$CERTS_DIR/bloggen-ca.conf" -key "$CERTS_DIR/bloggen-ca-key.pem" -out "$CERTS_DIR/bloggen-ca.pem" -days 3650 -passin pass:bloggen-dev-ca

echo "✅ Certificate Authority created"

# Step 2: Create server certificates signed by our CA
echo "📋 Step 2: Creating server certificates..."

# Enhanced localhost configuration with all possible hostnames
cat > "$CERTS_DIR/localhost-enhanced.conf" << EOF
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
OU=Development Server
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

# Generate server private key
openssl genpkey -algorithm RSA -out "$CERTS_DIR/localhost-key.pem" -pkcs8 2>/dev/null

# Generate certificate signing request
openssl req -new -config "$CERTS_DIR/localhost-enhanced.conf" -key "$CERTS_DIR/localhost-key.pem" -out "$CERTS_DIR/localhost.csr"

# Create server certificate signed by our CA
openssl x509 -req -in "$CERTS_DIR/localhost.csr" -CA "$CERTS_DIR/bloggen-ca.pem" -CAkey "$CERTS_DIR/bloggen-ca-key.pem" -CAcreateserial -out "$CERTS_DIR/localhost.pem" -days 365 -extensions v3_req -extfile "$CERTS_DIR/localhost-enhanced.conf" -passin pass:bloggen-dev-ca

echo "✅ Server certificates created"

# Step 3: Copy certificates to frontend
echo "📋 Step 3: Setting up frontend certificates..."
cp "$CERTS_DIR/localhost.pem" "$FRONTEND_CERTS_DIR/"
cp "$CERTS_DIR/localhost-key.pem" "$FRONTEND_CERTS_DIR/"
cp "$CERTS_DIR/bloggen-ca.pem" "$FRONTEND_CERTS_DIR/"

echo "✅ Frontend certificates configured"

# Step 4: System-level CA installation (requires sudo)
echo "📋 Step 4: Installing Certificate Authority system-wide..."

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux (Ubuntu/Debian)
    if command -v update-ca-certificates >/dev/null; then
        echo "📝 Installing CA certificate for Linux..."
        sudo cp "$CERTS_DIR/bloggen-ca.pem" /usr/local/share/ca-certificates/bloggen-ca.crt
        sudo update-ca-certificates
        echo "✅ CA certificate installed system-wide (Linux)"
    else
        echo "⚠️  Manual installation required: Add $CERTS_DIR/bloggen-ca.pem to your system's trust store"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "📝 Installing CA certificate for macOS..."
    sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "$CERTS_DIR/bloggen-ca.pem"
    echo "✅ CA certificate installed system-wide (macOS)"
else
    echo "⚠️  Manual installation required for your OS"
fi

# Step 5: Browser-specific instructions
echo "📋 Step 5: Browser configuration instructions..."

cat << EOF

🌐 BROWSER CONFIGURATION REQUIRED
==================================

For permanent SSL certificate trust, you need to:

1. 🦊 Firefox:
   - Open Firefox
   - Go to about:preferences#privacy
   - Scroll to "Certificates" → Click "View Certificates"
   - Go to "Authorities" tab → Click "Import"
   - Select: $CERTS_DIR/bloggen-ca.pem
   - Check "Trust this CA to identify websites"

2. 🌍 Chrome/Edge:
   - Open Chrome/Edge
   - Go to chrome://settings/certificates (or edge://settings/certificates)
   - Click "Authorities" tab → Click "Import"
   - Select: $CERTS_DIR/bloggen-ca.pem
   - Check "Trust this certificate for identifying websites"

3. 🖥️  System Trust (Already attempted):
   - Linux: Certificate added to /usr/local/share/ca-certificates/
   - macOS: Certificate added to System Keychain

EOF

# Step 6: Application configuration
echo "📋 Step 6: Updating application configuration..."

# Update backend environment
if [ -f "$PROJECT_ROOT/backend/.env" ]; then
    # Backup existing .env
    cp "$PROJECT_ROOT/backend/.env" "$PROJECT_ROOT/backend/.env.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Update SSL certificate paths
    sed -i.bak "s|SSL_CERT_PATH=.*|SSL_CERT_PATH=$CERTS_DIR/localhost.pem|g" "$PROJECT_ROOT/backend/.env" 2>/dev/null || true
    sed -i.bak "s|SSL_KEY_PATH=.*|SSL_KEY_PATH=$CERTS_DIR/localhost-key.pem|g" "$PROJECT_ROOT/backend/.env" 2>/dev/null || true
    
    # Add SSL configuration if not present
    if ! grep -q "SSL_CERT_PATH" "$PROJECT_ROOT/backend/.env"; then
        echo "" >> "$PROJECT_ROOT/backend/.env"
        echo "# SSL Certificate Configuration" >> "$PROJECT_ROOT/backend/.env"
        echo "SSL_CERT_PATH=$CERTS_DIR/localhost.pem" >> "$PROJECT_ROOT/backend/.env"
        echo "SSL_KEY_PATH=$CERTS_DIR/localhost-key.pem" >> "$PROJECT_ROOT/backend/.env"
        echo "SSL_CA_PATH=$CERTS_DIR/bloggen-ca.pem" >> "$PROJECT_ROOT/backend/.env"
    fi
fi

echo "✅ Application configuration updated"

# Step 7: Node.js certificate configuration
echo "📋 Step 7: Configuring Node.js SSL handling..."

# Create Node.js SSL configuration file
cat > "$PROJECT_ROOT/frontend-nextjs/blog-generator-ui/ssl-config.js" << EOF
// SSL Configuration for Node.js development
const fs = require('fs');
const path = require('path');

// Path to our custom CA certificate
const caPath = path.join(__dirname, 'certs', 'bloggen-ca.pem');

if (fs.existsSync(caPath)) {
    // Add our custom CA to Node.js trusted certificates
    process.env.NODE_EXTRA_CA_CERTS = caPath;
    console.log('🔒 Custom CA certificate loaded for Node.js');
} else {
    console.warn('⚠️  Custom CA certificate not found at:', caPath);
}

module.exports = {
    caPath,
    certPath: path.join(__dirname, 'certs', 'localhost.pem'),
    keyPath: path.join(__dirname, 'certs', 'localhost-key.pem')
};
EOF

echo "✅ Node.js SSL configuration created"

# Step 8: Create verification script
cat > "$PROJECT_ROOT/verify-ssl.sh" << 'EOF'
#!/bin/bash

echo "🔍 SSL Certificate Verification"
echo "================================"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="$PROJECT_ROOT/certs"

# Test certificate validity
echo "📋 Testing certificate validity..."
openssl x509 -in "$CERTS_DIR/localhost.pem" -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After:|DNS:|IP Address:)"

echo ""
echo "📋 Testing HTTPS connections..."

# Test backend
echo "🔧 Testing backend (port 5000)..."
if curl -s --cacert "$CERTS_DIR/bloggen-ca.pem" https://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ Backend HTTPS connection successful"
else
    echo "❌ Backend HTTPS connection failed"
fi

# Test frontend
echo "🔧 Testing frontend (port 3001)..."
if curl -s --cacert "$CERTS_DIR/bloggen-ca.pem" https://localhost:3001/ > /dev/null 2>&1; then
    echo "✅ Frontend HTTPS connection successful"
else
    echo "❌ Frontend HTTPS connection failed (may be normal if not running)"
fi

echo ""
echo "📋 Browser instructions:"
echo "1. Import $CERTS_DIR/bloggen-ca.pem into your browser's certificate authorities"
echo "2. Restart your browser after importing"
echo "3. Visit https://localhost:3001 - should show secure connection"
EOF

chmod +x "$PROJECT_ROOT/verify-ssl.sh"

echo "✅ Verification script created"

# Step 9: Create package.json scripts for frontend
if [ -f "$PROJECT_ROOT/frontend-nextjs/blog-generator-ui/package.json" ]; then
    echo "📋 Step 9: Updating frontend package.json scripts..."
    
    # Create updated dev-dynamic.js with SSL config
    cat > "$PROJECT_ROOT/frontend-nextjs/blog-generator-ui/dev-dynamic.js" << 'EOF'
// SSL Configuration
require('./ssl-config');

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
    console.log(`🔒 HTTPS Server ready on https://${hostname}:${port}`);
    console.log(`🔒 SSL certificates: Custom CA-signed certificates`);
  });
});
EOF
    
    echo "✅ Frontend SSL configuration updated"
fi

# Final summary
echo ""
echo "🎉 SSL CERTIFICATE SETUP COMPLETE!"
echo "=================================="
echo ""
echo "📋 What was created:"
echo "  • Custom Certificate Authority (CA): $CERTS_DIR/bloggen-ca.pem"
echo "  • Server certificate: $CERTS_DIR/localhost.pem"
echo "  • Server private key: $CERTS_DIR/localhost-key.pem"
echo "  • System-wide CA installation (attempted)"
echo "  • Frontend SSL configuration"
echo "  • Node.js SSL configuration"
echo ""
echo "📋 Next steps:"
echo "  1. Import the CA certificate into your browser (see instructions above)"
echo "  2. Restart your browser"
echo "  3. Run: ./verify-ssl.sh to test the setup"
echo "  4. Start your applications with HTTPS enabled"
echo ""
echo "📋 Troubleshooting:"
echo "  • If still getting SSL errors: Restart browser after importing CA"
echo "  • For system-wide trust issues: Reboot your system"
echo "  • Manual import: Use $CERTS_DIR/bloggen-ca.pem in browser settings"
echo ""
echo "🔒 Your development environment now has a proper SSL Certificate Authority!"
