#!/usr/bin/env node
/**
 * Dynamic development server for Next.js
 * Automatically chooses HTTP or HTTPS based on NEXT_PUBLIC_PROTOCOL_MODE
 */

// Disable SSL verification for development (allows self-signed certificates)
process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

const { spawn } = require('child_process');
const https = require('https');
const fs = require('fs');
const path = require('path');

// Read .env.local file
let PROTOCOL_MODE = 'https'; // default
try {
  const envPath = path.join(__dirname, '.env.local');
  const envContent = fs.readFileSync(envPath, 'utf8');
  const envLines = envContent.split('\n');
  
  for (const line of envLines) {
    if (line.startsWith('NEXT_PUBLIC_PROTOCOL_MODE=')) {
      PROTOCOL_MODE = line.split('=')[1].trim();
      break;
    }
  }
} catch (error) {
  console.log('Could not read .env.local, using default HTTPS mode');
}
const HOST = 'localhost';
const PORT = '3001';

console.log(`🔧 Protocol Config: ${PROTOCOL_MODE.toUpperCase()} mode`);
console.log(`   Frontend: ${PROTOCOL_MODE}://${HOST}:${PORT}`);

if (PROTOCOL_MODE === 'https') {
  // HTTPS mode - use dev-https.js
  console.log(`🔒 Starting HTTPS development server...`);
  
  const certPath = path.join(__dirname, '../../certs/localhost.pem');
  const keyPath = path.join(__dirname, '../../certs/localhost-key.pem');
  
  if (!fs.existsSync(certPath) || !fs.existsSync(keyPath)) {
    console.error(`❌ SSL certificates not found:`);
    console.error(`   Cert: ${certPath}`);
    console.error(`   Key: ${keyPath}`);
    console.error(`   Run: openssl req -x509 -newkey rsa:4096 -keyout certs/localhost-key.pem -out certs/localhost.pem -days 365 -nodes -subj "/CN=localhost"`);
    process.exit(1);
  }
  
  // Use the existing dev-https.js
  const httpsServer = spawn('node', ['dev-https.js'], {
    stdio: 'inherit',
    cwd: __dirname,
    env: { 
      ...process.env, 
      NODE_TLS_REJECT_UNAUTHORIZED: '0' 
    }
  });
  
  httpsServer.on('close', (code) => {
    console.log(`HTTPS server exited with code ${code}`);
  });
  
} else {
  // HTTP mode - use regular Next.js dev
  console.log(`🔓 Starting HTTP development server...`);
  
  const httpServer = spawn('npx', ['next', 'dev', '--hostname', HOST, '--port', PORT], {
    stdio: 'inherit',
    cwd: __dirname,
    env: { 
      ...process.env, 
      NODE_TLS_REJECT_UNAUTHORIZED: '0' 
    }
  });
  
  httpServer.on('close', (code) => {
    console.log(`HTTP server exited with code ${code}`);
  });
}
