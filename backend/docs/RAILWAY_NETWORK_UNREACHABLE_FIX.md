# Railway "Network is unreachable" Error - Troubleshooting Guide

## 🚨 Problem
Railway deployment fails with:
```
OSError: [Errno 101] Network is unreachable
```

This error occurs **before** any authentication attempt - it's a network routing issue where Railway's infrastructure **cannot establish a TCP connection** to Supabase.

## 🔍 Root Causes

### 1. **Supabase IP Allowlist (MOST LIKELY)**

Supabase has IP restrictions that block Railway's dynamic IPs.

**Check:**
1. Go to Supabase Dashboard → Your Project
2. Navigate to **Settings → Database**
3. Look for **"Connection pooling"** or **"Network Restrictions"** section
4. Check if **"Restrict connections to specific IP addresses"** is enabled

**Solution:**
- **Option A (Recommended):** Disable IP restrictions for connection pooler
  - In Supabase: Settings → Database → Connection pooling → Disable IP restrictions
  - Or add `0.0.0.0/0` to allow all IPs (less secure but works for testing)

- **Option B:** Use Supabase's IPv6 endpoint (if Railway supports IPv6)
  - Try: `postgresql://...@db.PROJECT.supabase.co:5432/postgres` (direct connection)

- **Option C:** Get Railway's static IP (paid feature)
  - Railway Pro plan offers static IPs
  - Add Railway's static IP to Supabase allowlist

### 2. **IPv4 vs IPv6 Routing Issue**

Railway might be IPv4-only, while Supabase prefers IPv6.

**Test locally:**
```bash
# Check what IPs your Supabase endpoint resolves to
nslookup db.agaejevkyzufcqptatdw.supabase.co
nslookup aws-0-eu-west-3.pooler.supabase.com

# Test connection from Railway-like environment
docker run --rm -it postgres:15 psql "postgresql://postgres.PROJECT:PASSWORD@db.PROJECT.supabase.co:5432/postgres"
```

**Solution:**
- Use direct connection endpoint: `db.PROJECT.supabase.co:5432`
- Contact Railway support about IPv6 support

### 3. **Region-Specific Network Restrictions**

Railway's region cannot route to Supabase's EU region.

**Check:**
- Your Supabase is in: `eu-west-3` (Paris)
- Railway might be deploying to: US-West or different region

**Solution:**
1. Check Railway deployment region in dashboard
2. Try changing Railway region to Europe:
   - Railway Dashboard → Settings → Region → Select Europe
3. Or move Supabase to a more globally accessible region

### 4. **Firewall/Security Group Issues**

Supabase or Railway has strict firewall rules.

**Solution:**
- Check Supabase project status (not paused)
- Verify database is accessible from public internet
- Test with `telnet` or `nc` from another server

## ✅ Immediate Actions (In Order)

### Action 1: Check Supabase IP Restrictions (DO THIS FIRST!)

```bash
# 1. Go to Supabase Dashboard
# 2. Settings → Database
# 3. Look for "Network Restrictions" or "IP Allowlist"
# 4. If enabled, add 0.0.0.0/0 or disable restrictions
```

**This is the #1 cause of Railway connection failures!**

### Action 2: Try Connection Pooler with Session Mode

Update Railway `DATABASE_URL` to:
```
postgresql://postgres.PROJECT_REF:PASSWORD@db.PROJECT_REF.supabase.co:6543/postgres
```

This uses:
- Direct endpoint: `db.PROJECT.supabase.co` (not regional pooler)
- Port 6543: Transaction pooling mode
- Should have fewer network restrictions

### Action 3: Verify Supabase Project Status

1. Check project is **not paused** (free tier pauses after inactivity)
2. Check project has **no billing issues**
3. Verify **connection pooling is enabled**

### Action 4: Test from Railway Shell

Add a temporary Railway service to test connectivity:

1. Create file `test-connection.sh`:
```bash
#!/bin/bash
apt-get update && apt-get install -y postgresql-client netcat
echo "Testing DNS resolution..."
nslookup db.agaejevkyzufcqptatdw.supabase.co
echo "Testing TCP connection..."
nc -zv db.agaejevkyzufcqptatdw.supabase.co 5432
echo "Testing PostgreSQL connection..."
psql "$DATABASE_URL" -c "SELECT version();"
```

2. Deploy and check logs to see where it fails

### Action 5: Use Supabase Direct Connection (No Pooler)

Update Railway `DATABASE_URL` to direct connection (port 5432):
```
postgresql://postgres.PROJECT_REF:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres
```

**Note:** Direct connection has connection limits (max ~50), but might bypass pooler restrictions.

### Action 6: Enable Supabase Connection Pooling Mode "Session"

1. Supabase Dashboard → Settings → Database
2. Connection Pooling → Mode → Change to **"Session"** (not Transaction)
3. Use port **5432** for session pooling instead of 6543

## 🔧 Code Fix Applied

I've updated `database_service.py` to add explicit SSL configuration which might help with some network routing issues. However, this won't fix IP allowlist problems.

## 📊 Debugging Information to Collect

If issue persists, collect this info:

1. **Supabase Settings**
   - Project region: `eu-west-3` ✓
   - IP restrictions: `?` ← CHECK THIS
   - Connection pooling mode: `?`
   - Pooling port: `6543` or `5432`?

2. **Railway Settings**
   - Deployment region: `?` ← CHECK THIS
   - Service type: Web service
   - Environment: Production

3. **Connection String Being Used**
   - Hostname: `db.agaejevkyzufcqptatdw.supabase.co` or `aws-0-eu-west-3.pooler.supabase.com`?
   - Port: `5432` or `6543`?

## 🎯 Most Likely Solution

**90% chance it's Supabase IP restrictions.** 

Go to Supabase Dashboard → Settings → Database → Disable IP restrictions or add `0.0.0.0/0` to allowlist.

## 📚 Related Resources

- [Supabase Network Restrictions](https://supabase.com/docs/guides/platform/network-restrictions)
- [Railway Networking Guide](https://docs.railway.app/reference/networking)
- [asyncpg SSL Documentation](https://magicstack.github.io/asyncpg/current/api/index.html#asyncpg.connection.connect)
