# 🔒 SSL Certificate Trust Guide

If you encounter SSL certificate errors when using the blog generation features, follow these steps to trust the development SSL certificate:

## Quick Fix
1. **Open Backend URL**: Visit [https://localhost:5000](https://localhost:5000) in your browser
2. **Accept Certificate**: Click "Advanced" → "Proceed to localhost (unsafe)"
3. **Return to App**: Go back to the blog generator and try again

## What This Does
- Adds the self-signed SSL certificate to your browser's trusted certificate store
- Allows HTTPS communication between frontend and backend
- Maintains secure development environment as required by the application

## Alternative Method
If the above doesn't work, you can also:
1. Visit any backend endpoint like [https://localhost:5000/health](https://localhost:5000/health)
2. Accept the certificate warning
3. Return to the main application

## Why This Happens
- The application uses HTTPS-only communication for security
- Development certificates are self-signed (not from a trusted CA)
- Browsers require manual acceptance of self-signed certificates

## Security Note
This is safe for development environments. The certificates are legitimate self-signed certificates created for local development.
