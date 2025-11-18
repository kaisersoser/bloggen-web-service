# 🔒 SSL Certificate Trust Guide

The development environment uses enhanced SSL certificates with proper Subject Alternative Names (SAN) for better browser compatibility.

## Quick Fix (Recommended)
1. **Open Backend URL**: Visit [https://localhost:5000](https://localhost:5000) in your browser
2. **Accept Certificate**: Click "Advanced" → "Proceed to localhost (unsafe)"
3. **Open Frontend URL**: Visit [https://localhost:3001](https://localhost:3001) in your browser  
4. **Accept Certificate**: Click "Advanced" → "Proceed to localhost (unsafe)"
5. **Return to App**: Navigate to [https://localhost:3001/blog](https://localhost:3001/blog)

## Enhanced Certificate Features
- ✅ **Subject Alternative Names (SAN)** included for localhost, 127.0.0.1, and IPv6
- ✅ **2048-bit RSA encryption** for better security
- ✅ **SHA-256 signature** algorithm
- ✅ **365-day validity** period

## Regenerating Certificates
If you need to regenerate certificates:
```bash
cd /home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service
./restart-servers.sh
```

## Alternative Method
If the above doesn't work, you can also:
1. Visit any backend endpoint like [https://localhost:5000/health](https://localhost:5000/health)
2. Accept the certificate warning
3. Return to the main application

## Why This Happens
- The application uses HTTPS-only communication for security
- Development certificates are self-signed (not from a trusted CA)
- Browsers require manual acceptance of self-signed certificates
- New certificates include proper SAN fields for better compatibility

## Security Note
This is safe for development environments. The certificates are legitimate self-signed certificates created for local development with industry-standard encryption.
