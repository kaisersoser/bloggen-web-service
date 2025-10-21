# Frontend Logging and Debug Mode Setup

## 🚀 Overview
The frontend is now running in **full debug mode** with comprehensive logging capabilities for detailed analysis.

## 📝 Log File Location
```
/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/frontend-nextjs/blog-generator-ui/frontend.log
```

All frontend output including:
- Debug messages (`DEBUG=*`)
- Next.js router events
- Compilation status
- HTTP requests
- Errors and warnings
- Inspector/debugger output

## ✅ Current Status

### Frontend Service
- **Status**: ✅ Running
- **PID**: 380435
- **Port**: 3001 (HTTPS)
- **URLs**: 
  - https://localhost:3001
  - https://192.168.1.79:3001
  - https://vogtcha-MS-7B12:3001
- **Response Time**: 0.025s

### Debug Configuration
```bash
NODE_ENV=development     # Development mode
DEBUG=*                  # Full debug output enabled
NODE_OPTIONS='--inspect' # Node.js inspector enabled
```

### Server Configuration
- ✅ HTTPS mode enabled
- ✅ SSL certificates loaded
- ✅ Hot module replacement active
- ✅ Fast refresh enabled
- ✅ TypeScript compilation active

## 🛠️ Monitoring Tools

### 1. Real-Time Log Monitoring (Color-coded)
```bash
# Watch the log file in real-time with colors
./monitor_frontend.sh
```

**Features:**
- 🔴 Red: Errors and exceptions
- 🟡 Yellow: Warnings
- 🟢 Green: Success messages, compilations
- 🔵 Cyan: HTTPS/SSL messages
- 🟣 Magenta: Configuration messages
- 🔵 Blue: Next.js debug messages

**Example output:**
```
🔒 HTTPS Server ready on:
   https://localhost:3001
✅ Compiled successfully
 GET / 200 in 51ms
```

### 2. Status Check Script
```bash
# Quick health check of frontend
./check_frontend_status.sh
```

**Checks:**
- ✅ Process running
- ✅ Port 3001 listening
- ✅ HTTPS server responding
- ✅ Compilation status
- ✅ Recent errors/warnings
- ✅ Debug mode active

### 3. Direct Log Access
```bash
# Show last 50 lines
tail -50 frontend.log

# Follow log in real-time
tail -f frontend.log

# Search for errors
grep -i error frontend.log

# Search for compilation events
grep "compiled" frontend.log

# Show debug messages
grep "DEBUG" frontend.log | head -20

# Monitor specific route requests
grep "GET /admin" frontend.log

# Check HTTPS initialization
grep "HTTPS" frontend.log
```

## 📊 Debug Output Examples

### Next.js Router Debug
```
next:router-server:main invokeRender / 
next:router-server:filesystem nextDataRoutes Set(0) {}
next:router-server:filesystem dynamicRoutes []
```

### Request Logging
```
GET / 200 in 51ms
GET /admin/monitoring 200 in 123ms
POST /api/blog/generate 200 in 2341ms
```

### Compilation Events
```
✅ Compiled successfully in 2.3s
⚠️  Compiled with warnings in 1.5s
❌ Failed to compile
```

## 🔍 Advanced Debug Features

### Node.js Inspector
The inspector is available on port 9229 (may conflict if multiple instances):
```
Starting inspector on 127.0.0.1:9229
```

**To use Chrome DevTools:**
1. Open Chrome/Edge
2. Navigate to `chrome://inspect`
3. Click "inspect" under your Node.js process
4. Use breakpoints, profiling, memory analysis

### Environment Variables Debug
Check loaded environment variables:
```bash
grep "NODE_ENV\|DEBUG\|NEXT_PUBLIC" frontend.log | head -20
```

### SSL/TLS Debug
Monitor HTTPS certificate usage:
```bash
grep -i "ssl\|tls\|certificate" frontend.log
```

## 📈 Log Analysis Commands

### Performance Analysis
```bash
# Show response times for all requests
grep -oP "in \K[0-9]+ms" frontend.log | sort -n | tail -20

# Count requests by route
grep "GET " frontend.log | awk '{print $2}' | sort | uniq -c | sort -rn

# Average response time (rough calculation)
grep -oP "in \K[0-9]+" frontend.log | awk '{s+=$1; c++} END {print s/c "ms average"}'
```

### Error Pattern Detection
```bash
# Find unique errors
grep -i error frontend.log | sort | uniq -c | sort -rn

# Errors with timestamps
grep -i error frontend.log | grep "2025-10-14"

# Group errors by hour
grep -i error frontend.log | grep -oP "T\K[0-9]{2}:" | sort | uniq -c
```

### Compilation Tracking
```bash
# Count successful compilations
grep -c "compiled successfully" frontend.log

# Show compilation times
grep "compiled" frontend.log | grep -oP "in \K[0-9.]+s"

# Latest compilation status
grep "compiled" frontend.log | tail -5
```

## 🎯 Common Debug Scenarios

### 1. Page Not Loading
```bash
# Check if route is registered
grep "pathname.*your-route" frontend.log

# Check for errors during page render
tail -f frontend.log | grep -i "error\|exception"

# Monitor specific page requests
tail -f frontend.log | grep "/your-route"
```

### 2. API Connection Issues
```bash
# Monitor API calls to backend
grep "localhost:5000" frontend.log

# Check for fetch errors
grep -i "fetch.*error" frontend.log

# Track API response times
grep "api.*in.*ms" frontend.log
```

### 3. Authentication Problems
```bash
# Monitor auth routes
grep "/api/auth" frontend.log

# Check NextAuth debug messages
grep "next-auth" frontend.log

# Session-related events
grep -i "session" frontend.log
```

### 4. Database Pool Monitoring (via Frontend)
```bash
# Monitor database pool dashboard requests
tail -f frontend.log | grep "/admin/monitoring"

# Check health endpoint calls
grep "health/database-pool" frontend.log

# Track SSE connections
grep -i "sse\|stream" frontend.log
```

## 🔧 Debug Configuration

### Current Launch Command
```bash
NODE_ENV=development DEBUG=* NODE_OPTIONS='--inspect' nohup npm run dev > frontend.log 2>&1 &
```

### Adjust Debug Level
To change debug output granularity:

**Less verbose (Next.js only):**
```bash
DEBUG=next:* npm run dev > frontend.log 2>&1 &
```

**Router only:**
```bash
DEBUG=next:router* npm run dev > frontend.log 2>&1 &
```

**No debug (errors/warnings only):**
```bash
npm run dev > frontend.log 2>&1 &
```

**Maximum verbosity (current):**
```bash
DEBUG=* npm run dev > frontend.log 2>&1 &
```

### Enable Source Maps
For better error stack traces (already enabled in development):
```bash
# In next.config.js
productionBrowserSourceMaps: true
```

## 📁 Log Management

### Current Log
```bash
# Current session log
tail -f frontend.log
```

### Archive Logs
```bash
# Create archive directory
mkdir -p logs/archive

# Archive current log with timestamp
mv frontend.log logs/archive/frontend_$(date +%Y%m%d_%H%M%S).log

# Restart frontend with new log
NODE_ENV=development DEBUG=* npm run dev > frontend.log 2>&1 &
```

### Log Rotation
For automatic log rotation, create a logrotate config:
```bash
cat > /etc/logrotate.d/frontend << EOF
/path/to/frontend.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF
```

## 🧪 Testing with Logs

### Monitor During Blog Generation
```bash
# Terminal 1: Monitor frontend log
./monitor_frontend.sh

# Terminal 2: Monitor backend log
cd ../../backend && ./monitor_log.sh

# Terminal 3: Generate blog
# Use browser at https://localhost:3001
```

### Track SSE Streaming
```bash
# Watch for SSE connections and updates
tail -f frontend.log | grep -i "sse\|stream\|event"
```

### Monitor Dashboard Updates
```bash
# Watch monitoring dashboard requests
tail -f frontend.log | grep "/admin/monitoring"
```

## 🐛 Troubleshooting

### Frontend Won't Start
```bash
# Check if port is in use
lsof -i :3001

# Kill existing processes
pkill -f "dev-https\|dev-dynamic"

# Restart frontend
NODE_ENV=development DEBUG=* npm run dev > frontend.log 2>&1 &
```

### No Debug Output in Log
```bash
# Verify DEBUG environment variable
ps aux | grep "node.*dev" | grep -o "DEBUG=[^ ]*"

# Should show: DEBUG=*

# If not, restart with explicit DEBUG
DEBUG=* npm run dev > frontend.log 2>&1 &
```

### Compilation Errors
```bash
# Show full compilation error
grep -A 20 "Failed to compile" frontend.log

# Check TypeScript errors
grep -i "typescript\|type error" frontend.log

# Module resolution issues
grep -i "cannot find module" frontend.log
```

### HTTPS Certificate Issues
```bash
# Check certificate status
grep -i "certificate\|ssl" frontend.log

# Verify cert files exist
ls -la ../../certs/localhost*.pem

# Check cert expiration
openssl x509 -in ../../certs/localhost.pem -noout -dates
```

## 📊 Performance Metrics

### Response Time Statistics
```bash
# Get basic stats from log
echo "Response time analysis (last 100 requests):"
grep -oP "in \K[0-9]+" frontend.log | tail -100 | awk '
  {
    sum+=$1; 
    count++; 
    if(min=="" || $1<min) min=$1; 
    if($1>max) max=$1
  } 
  END {
    print "  Average: " sum/count "ms"
    print "  Min: " min "ms"
    print "  Max: " max "ms"
  }'
```

### Request Distribution
```bash
# Requests per route
echo "Top 10 requested routes:"
grep -oP "GET \K[^ ]+" frontend.log | sort | uniq -c | sort -rn | head -10
```

## 🎯 Integration with Backend

### Simultaneous Monitoring
Create a split-screen monitoring setup:

**Terminal 1 (Backend):**
```bash
cd /home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend
./monitor_log.sh
```

**Terminal 2 (Frontend):**
```bash
cd /home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/frontend-nextjs/blog-generator-ui
./monitor_frontend.sh
```

**Terminal 3 (Interactive):**
```bash
# Run tests, check status, etc.
```

### Coordinated Log Analysis
```bash
# Find errors in both logs
echo "=== Backend Errors ==="
grep ERROR ../../backend/backend.log | tail -5
echo ""
echo "=== Frontend Errors ==="
grep -i error frontend.log | tail -5
```

## 📚 Related Documentation

- **Backend Logging**: `../../backend/docs/BACKEND_LOGGING_SETUP.md`
- **Database Pool Fix**: `../../backend/docs/DATABASE_POOL_CLOSED_DEFAULT_FIX.md`
- **Monitoring Dashboard**: `../../docs/DATABASE_POOL_MONITORING_DASHBOARD.md`
- **Smooth Updates**: `../../docs/SMOOTH_GRAPH_UPDATES.md`

## 🎉 Summary

✅ **Frontend**: Running in full debug mode on port 3001  
✅ **Logging**: All output captured in `frontend.log`  
✅ **Debug Level**: Maximum (`DEBUG=*`)  
✅ **Inspector**: Node.js debugger available  
✅ **Monitoring**: Scripts available for real-time tracking  
✅ **HTTPS**: SSL certificates loaded and working  

**Ready for detailed analysis and debugging!**

---

**Last Updated**: October 14, 2025  
**Frontend PID**: 380435  
**Log File**: `frontend-nextjs/blog-generator-ui/frontend.log`  
**Status**: ✅ Fully Operational in Debug Mode  
**URLs**: https://localhost:3001
