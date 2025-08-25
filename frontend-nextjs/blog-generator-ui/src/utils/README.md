# Frontend Utilities

This directory contains utility scripts and development tools for the frontend application.

## Utility Scripts

### Development Servers
- **`dev-dynamic.js`** - Dynamic development server (auto-detects HTTP/HTTPS mode)
- **`dev-https.js`** - HTTPS development server with SSL certificates

### Setup Scripts
- **`setup-auth.sh`** - Authentication setup script (NextAuth.js + PostgreSQL)
- **`setup-supabase.sh`** - Supabase configuration and setup script  
- **`setup-local-https.sh`** - Local HTTPS certificates and SSL setup script

## Usage

### Development Servers
```bash
# Dynamic server (reads NEXT_PUBLIC_PROTOCOL_MODE from .env.local)
node src/utils/dev-dynamic.js

# Force HTTPS server
node src/utils/dev-https.js
```

### Setup Scripts
```bash
# Setup authentication system
./src/utils/setup-auth.sh

# Setup Supabase integration  
./src/utils/setup-supabase.sh

# Setup local HTTPS certificates
./src/utils/setup-local-https.sh
```

## Script Details

### Development Servers
- **Auto-protocol detection** based on environment variables
- **SSL certificate handling** for HTTPS development
- **Request routing** and middleware integration

### Setup Scripts
- **Dependency installation** and configuration
- **Environment file setup** and validation
- **Database schema** initialization
- **SSL certificate generation** for local development

## Requirements
- Node.js runtime for JavaScript utilities
- Bash shell for setup scripts
- Valid .env.local configuration
- SSL certificates in `certs/` directory (for HTTPS)

## Notes
- All scripts are designed for development environments
- HTTPS scripts require valid SSL certificates
- Setup scripts should be run from project root directory
