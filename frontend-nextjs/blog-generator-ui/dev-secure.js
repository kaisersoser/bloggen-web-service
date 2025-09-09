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
