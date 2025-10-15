# 🤖 Deployment Automation Scripts

This directory contains production-ready automation scripts for deploying and managing your BlogGen web service.

---

## 📋 Available Scripts

### 1. `pre-deploy-check.sh`
**Purpose:** Validates your application is ready for production deployment

**Usage:**
```bash
./scripts/pre-deploy-check.sh
```

**What it checks:**
- Git repository status and cleanliness
- Python and Node.js versions
- Critical files existence
- No hardcoded secrets in code
- Syntax errors in Python/TypeScript
- Dependencies configuration
- Docker configuration
- Documentation completeness

**Exit codes:**
- `0` - All checks passed, ready to deploy
- `1` - Critical issues found, fix before deploying

---

### 2. `deploy-production.sh`
**Purpose:** Automated deployment to Railway (backend) and Vercel (frontend)

**Usage:**
```bash
# Full deployment (backend + frontend)
./scripts/deploy-production.sh

# Backend only
./scripts/deploy-production.sh --backend-only

# Frontend only
./scripts/deploy-production.sh --frontend-only

# Skip pre-checks (not recommended)
./scripts/deploy-production.sh --skip-checks
```

**What it does:**
1. Runs pre-deployment checks (unless `--skip-checks`)
2. Verifies Railway and Vercel CLI tools
3. Commits and pushes any pending changes
4. Deploys backend to Railway
5. Deploys frontend to Vercel
6. Runs health checks on deployed services
7. Saves deployment log to `deployments/`

**Output:**
- Real-time deployment progress
- Deployment URLs
- Health check results
- Deployment log file

---

### 3. `rollback.sh`
**Purpose:** Safely rolls back to previous deployment

**Usage:**
```bash
# Interactive rollback (prompts for version)
./scripts/rollback.sh

# Rollback backend only
./scripts/rollback.sh --backend

# Rollback frontend only
./scripts/rollback.sh --frontend

# Rollback to specific commit
./scripts/rollback.sh --to-commit abc123def
```

**What it does:**
1. Shows recent deployments or git commits
2. Prompts for target version
3. Creates safety backup branch
4. Reverts code to target version
5. Triggers redeployment
6. Runs health checks
7. Saves rollback log to `rollbacks/`

**Safety features:**
- Creates backup branch automatically
- Uses `git revert` (preserves history)
- Requires multiple confirmations
- Validates target commit exists

---

### 4. `health-check.sh`
**Purpose:** Comprehensive health check for production deployment

**Usage:**
```bash
# With URLs
./scripts/health-check.sh https://api.example.com https://example.com

# Interactive (will prompt for URLs)
./scripts/health-check.sh
```

**What it checks:**
- Backend health endpoint
- Database pool status
- Redis connection
- Frontend homepage
- Authentication endpoints
- Static assets delivery
- CORS configuration
- Protected endpoints (auth required)
- SSL/TLS certificates
- Response times
- DNS resolution
- Network connectivity

**Output:**
- Detailed check results (pass/fail/warning)
- Response times
- HTTP status codes
- SSL certificate validity
- Overall health score (%)

**Exit codes:**
- `0` - All checks passed
- `1` - Critical issues detected

---

## 🚀 Quick Start

### First Time Setup

```bash
# 1. Make scripts executable (already done)
chmod +x scripts/*.sh

# 2. Verify scripts work
./scripts/pre-deploy-check.sh

# 3. If checks pass, you're ready!
```

### Typical Deployment Workflow

```bash
# Step 1: Pre-flight checks
./scripts/pre-deploy-check.sh

# Step 2: Deploy
./scripts/deploy-production.sh

# Step 3: Verify
./scripts/health-check.sh https://your-backend.up.railway.app https://your-frontend.vercel.app

# If issues: Rollback
./scripts/rollback.sh
```

---

## 📊 Script Dependencies

### Required Tools

**All scripts:**
- `bash` 4.0+
- `git` 2.0+

**deploy-production.sh:**
- `railway` CLI (optional, falls back to git push)
- `vercel` CLI (optional, falls back to git push)

**health-check.sh:**
- `curl`
- `openssl` (for SSL checks)
- `nslookup` (for DNS checks)
- `bc` (for numeric comparisons)

### Installing Optional CLIs

```bash
# Railway CLI
npm install -g @railway/cli

# Vercel CLI
npm install -g vercel

# Login to services
railway login
vercel login
```

---

## 🔧 Configuration

### Environment Variables

Scripts read from these sources:
1. Railway environment variables (set in dashboard)
2. Vercel environment variables (set in dashboard)
3. Git configuration

**No configuration files needed!** All settings managed through Railway/Vercel dashboards.

---

## 📁 Generated Files

Scripts create logs and backups:

```
bloggen-web-service/
├── deployments/
│   └── deployment-20251015-120000.log
│
├── rollbacks/
│   └── rollback-20251015-130000.log
│
└── backup-rollback-20251015-130000 (git branch)
```

### Deployment Log Format
```
Deployment Log
==============
Date: 2025-10-15 12:00:00
Branch: main
Commit: abc123def456
Backend URL: https://api.example.com
Frontend URL: https://example.com

Deployed Services:
  - Backend (Railway)
  - Frontend (Vercel)

Status: SUCCESS
```

### Rollback Log Format
```
Rollback Log
============
Date: 2025-10-15 13:00:00
From Commit: abc123def456
To Commit: def456abc123
Backup Branch: backup-rollback-20251015-130000
Branch: main

Rolled Back Services:
  - Backend (Railway)
  - Frontend (Vercel)

Reason: Manual rollback requested
Status: COMPLETED
```

---

## 🐛 Troubleshooting

### Script won't execute

```bash
# Make sure it's executable
chmod +x scripts/script-name.sh

# Check shebang line
head -n 1 scripts/script-name.sh
# Should be: #!/bin/bash
```

### "Command not found" errors

```bash
# Check which tool is missing
which railway
which vercel
which curl

# Install missing tools
npm install -g @railway/cli
npm install -g vercel
sudo apt-get install curl  # or brew install curl
```

### Pre-deployment checks fail

```bash
# See what failed
./scripts/pre-deploy-check.sh

# Common fixes:
# - Commit uncommitted changes
# - Fix syntax errors
# - Remove hardcoded secrets
# - Update dependencies
```

### Deployment fails

```bash
# Check logs
railway logs --tail 100
vercel logs --follow

# Verify environment variables
railway variables
vercel env ls

# Try manual deployment
cd backend && railway up
cd frontend-nextjs/blog-generator-ui && vercel --prod
```

### Health checks fail

```bash
# Test endpoints manually
curl https://api.example.com/health
curl https://example.com

# Check service status
railway status
vercel ls

# Review logs for errors
railway logs
vercel logs
```

---

## 🔒 Security Notes

### Safe Practices
✅ Scripts never expose secrets in logs  
✅ Uses environment variables, not files  
✅ Creates backup branches before rollback  
✅ Requires confirmation for destructive operations  
✅ Validates inputs before execution

### What NOT to do
❌ Don't commit `.env` files with secrets  
❌ Don't skip pre-deployment checks  
❌ Don't force push without backup  
❌ Don't run scripts without understanding what they do  
❌ Don't use production credentials locally

---

## 📈 Performance Tips

### Faster Deployments

```bash
# Use CLI tools for better control
npm install -g @railway/cli vercel

# Skip redundant checks (only if confident)
./scripts/deploy-production.sh --skip-checks

# Deploy only what changed
./scripts/deploy-production.sh --backend-only
./scripts/deploy-production.sh --frontend-only
```

### Efficient Health Checks

```bash
# Check critical endpoints only
curl https://api.example.com/health
curl https://api.example.com/health/database-pool

# Use monitoring tools for continuous checks
# - UptimeRobot
# - Better Uptime
# - Pingdom
```

---

## 🤝 Contributing

Want to improve these scripts?

### Adding Features

1. Create new script in `scripts/`
2. Make it executable: `chmod +x scripts/new-script.sh`
3. Follow naming convention: `kebab-case.sh`
4. Add header comment block
5. Update this README
6. Test thoroughly before committing

### Script Template

```bash
#!/bin/bash

# =============================================================================
# Script Name
# =============================================================================
# Description of what this script does
#
# Usage: ./scripts/script-name.sh [options]
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Your script logic here
```

---

## 📚 Related Documentation

- **Full Deployment Guide**: [../docs/DEPLOYMENT_GUIDE.md](../docs/DEPLOYMENT_GUIDE.md)
- **Quick Reference**: [../docs/DEPLOYMENT_QUICK_REFERENCE.md](../docs/DEPLOYMENT_QUICK_REFERENCE.md)
- **Environment Config**: [../docs/ENVIRONMENT_CONFIGURATION.md](../docs/ENVIRONMENT_CONFIGURATION.md)
- **Deployment Proposal**: [../PRODUCTION_DEPLOYMENT_PROPOSAL.md](../PRODUCTION_DEPLOYMENT_PROPOSAL.md)

---

## 🆘 Support

**Issues with scripts?**
1. Check troubleshooting section above
2. Review script output for error messages
3. Check Railway/Vercel status pages
4. Review logs: `railway logs` / `vercel logs`

**Need help?**
- Railway: https://railway.app/help
- Vercel: https://vercel.com/support
- GitHub Issues: Create an issue in your repository

---

**Happy Deploying! 🚀**

*Scripts last updated: October 15, 2025*
