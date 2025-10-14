# Database Pool Closure Investigation - Comprehensive Summary

**Date:** October 14, 2025  
**Issue:** Database connection pool closes after first blog generation, preventing subsequent blogs  
**Status:** 🔴 UNRESOLVED - Problem persists despite multiple fix attempts

---

## 🎯 Problem Description

### Symptoms
- **First blog generation:** ✅ Works perfectly
- **Subsequent blogs:** ❌ Fail with "Pool is closed" or "Pool unavailable" errors
- **Pool status after Blog #1:** `closed=true, initialized=false`
- **System behavior:** Must restart backend to generate another blog

### Observable Behavior
```json
// BEFORE first blog (healthy)
{
  "healthy": true,
  "stats": {
    "initialized": true,
    "closed": false,
    "size": 2,
    "free": 2,
    "in_use": 0
  }
}

// AFTER first blog (broken)
{
  "healthy": false,
  "stats": {
    "initialized": false,
    "closed": true,
    "size": 0,
    "free": 0,
    "in_use": 0
  }
}
```

---

## 🔍 Investigation Timeline

### Phase 1: Initial Discovery (Messages 1-5)
**Finding:** Pool showing as DEGRADED immediately after first blog completion

**Evidence from logs:**
```
Line 3259: Blog generation completed successfully
Line 3260: Pool becomes unavailable (closed=true)
```

**Key insight:** Pool object exists (`_pool is None: False`) but asyncpg marks it as `_closed=True`

---

### Phase 2: First Root Cause - `_closed` Default Bug (Messages 6-10)
**Problem:** `getattr(self._pool, '_closed', True)` defaulted to `True` for fresh pools

**Fix Applied:**
Changed default from `True` to `False` in 3 locations in `backend/src/core/database_service.py`:
- `ensure_pool()` line ~190
- `is_initialized()` line ~150
- `get_pool_stats()` line ~250

**Result:** ✅ Pool correctly detected as open initially, but **still closes after first blog**

---

### Phase 3: Event Loop Closure Discovery (Messages 11-20)
**Problem:** `new_loop.close()` in `backend/src/bloggen/flows.py` line 261

**Analysis:**
```python
# PROBLEMATIC CODE (line 261):
new_loop = asyncio.new_event_loop()
asyncio.set_event_loop(new_loop)
result = new_loop.run_until_complete(execute_with_rate_limiting())
new_loop.close()  # ❌ THIS CLOSES THE DATABASE POOL!
```

**Fix Applied:**
```python
# FIXED CODE:
new_loop = asyncio.new_event_loop()
asyncio.set_event_loop(new_loop)
result = new_loop.run_until_complete(execute_with_rate_limiting())
asyncio.set_event_loop(None)  # Clear reference without closing
# new_loop.close()  # REMOVED
```

**Result:** User tested - "Nope. Something is still closing our connections"

---

### Phase 4: Comprehensive Event Loop Analysis (Messages 21-35)
**Discovery:** Found **THREE** places closing event loops, not just one!

#### Culprit #1: `new_loop.close()` - Line 261 (Already Fixed)
```python
new_loop.close()  # REMOVED in Phase 3
```

#### Culprit #2: `asyncio.run()` - Line 279 (NEW DISCOVERY)
```python
# PROBLEMATIC:
result = asyncio.run(execute_with_rate_limiting())
# Python docs: "creates event loop, runs coroutine, CLOSES LOOP"
```

#### Culprit #3: `asyncio.run()` - Line 282 (NEW DISCOVERY)
```python
# PROBLEMATIC:
result = asyncio.run(execute_with_rate_limiting())
```

**Critical Insight from Python Documentation:**
> `asyncio.run()` - "This function runs the passed coroutine, taking care of managing the asyncio event loop, finalizing asynchronous generators, and **closing the loop**."

**Complete Fix Applied to ALL THREE locations:**
```python
# SAFE PATTERN (applied to lines 261, 279, 282):
manual_loop = asyncio.new_event_loop()
asyncio.set_event_loop(manual_loop)
try:
    result = manual_loop.run_until_complete(execute_with_rate_limiting())
finally:
    asyncio.set_event_loop(None)
    # DO NOT close: manual_loop.close()
```

**Files Modified:**
- `backend/src/bloggen/flows.py` - Lines 235-295 (all three execution paths)

**Result:** User tested - **"The same problem persists"**

---

### Phase 5: Code Loading Verification (Messages 36-42)
**Hypothesis:** Backend process running OLD code from memory

**Investigation:**
1. ✅ Verified fixes ARE in source files (`grep` confirmed)
2. ✅ Backend process PID 688080 started at 20:09
3. ❌ Fixes applied AFTER process started
4. 🔑 **Key insight:** Python doesn't hot-reload modules!

**Action Taken:**
- Killed PID 688080 (old code)
- Cleared `backend.log`
- Started fresh backend PID 739376 (new code)
- Verified pool healthy: `closed=false, initialized=true`

**Result:** User tested - **"The same problem persists. I was only able to create one blog."**

---

## 🛠️ Technical Details

### Database Service Architecture
**File:** `backend/src/core/database_service.py`

**Singleton Pattern:**
```python
class DatabaseService:
    _instance = None
    _instance_counter = 0
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance_counter += 1
            cls._instance = super().__new__(cls)
            cls._instance._instance_id = cls._instance_counter
        return cls._instance
```

**Pool Lifecycle:**
1. Pool created during app startup via `initialize()`
2. Pool borrowed via `get_connection()` context manager
3. Connections automatically returned to pool on context exit
4. Pool should remain open for entire application lifetime

### Blog Generation Flow
**File:** `backend/src/bloggen/flows.py`

**Three Execution Contexts:**
1. **Line 261:** New loop creation for rate limiting (has own event loop)
2. **Line 279:** Existing loop with running tasks (uses `run_until_complete`)
3. **Line 282:** No event loop in thread (creates manual loop)

**Rate Limiting Implementation:**
```python
async def execute_with_rate_limiting():
    async with self.rate_limiter:
        return await self._execute_flow_with_timeout(
            self.crew.kickoff_async(inputs=inputs),
            phase_name=phase_name
        )
```

### asyncpg Pool Behavior
**Key Finding:** asyncpg pools are tied to event loops. When an event loop closes:
- Pool's internal `_closed` flag set to `True`
- Pool becomes unusable
- No automatic recovery mechanism

---

## 📝 All Fixes Applied

### Fix #1: `_closed` Default Value
**File:** `backend/src/core/database_service.py`

**Changes:**
```python
# BEFORE:
is_closed = getattr(self._pool, '_closed', True)  # ❌ Wrong default

# AFTER:
is_closed = getattr(self._pool, '_closed', False)  # ✅ Correct default
```

**Locations:** Lines ~150, ~190, ~250

---

### Fix #2: Remove `new_loop.close()` - Line 261
**File:** `backend/src/bloggen/flows.py`

**Changes:**
```python
# BEFORE:
new_loop = asyncio.new_event_loop()
asyncio.set_event_loop(new_loop)
result = new_loop.run_until_complete(execute_with_rate_limiting())
new_loop.close()  # ❌ CLOSES POOL

# AFTER:
new_loop = asyncio.new_event_loop()
asyncio.set_event_loop(new_loop)
result = new_loop.run_until_complete(execute_with_rate_limiting())
asyncio.set_event_loop(None)  # ✅ Clear without closing
# new_loop.close()  # REMOVED
```

---

### Fix #3: Replace `asyncio.run()` - Line 279
**File:** `backend/src/bloggen/flows.py`

**Changes:**
```python
# BEFORE:
result = asyncio.run(execute_with_rate_limiting())  # ❌ Auto-closes loop

# AFTER:
manual_loop = asyncio.new_event_loop()
asyncio.set_event_loop(manual_loop)
try:
    result = manual_loop.run_until_complete(execute_with_rate_limiting())
finally:
    asyncio.set_event_loop(None)
    # DO NOT close: manual_loop.close()
```

---

### Fix #4: Replace `asyncio.run()` - Line 282
**File:** `backend/src/bloggen/flows.py`

**Changes:** Same as Fix #3 (different code path, same pattern)

---

### Fix #5: Enhanced Debugging
**File:** `backend/src/core/database_service.py`

**Added:**
- Instance counter and ID tracking
- Pool object ID logging
- Stack traces on `close()` calls
- Detailed warnings with pool diagnostics
- Connection detail verification

**Debug Output Example:**
```
🆕 DatabaseService instance #1 created
✅ Pool created for instance #1: pool_id=140493846739456
⚠️ Instance #1: Pool unavailable in get_pool_stats()
   _pool is None: False
   _pool object id: 140493846739456
   Have connection details: True
```

---

## 🧪 Testing Performed

### Test 1: Initial Pool Status (After All Fixes)
```bash
curl -k https://localhost:5000/health/database-pool
```
**Result:** ✅ `closed=false, initialized=true, size=2`

### Test 2: First Blog Generation
**Result:** ✅ Blog generated successfully

### Test 3: Pool Status After First Blog
**Result:** ❌ `closed=true, initialized=false, size=0`

### Test 4: Second Blog Generation
**Result:** ❌ "Pool is closed" error

### Test 5: Backend Restart + Retry
**Result:** Same pattern - first blog works, second fails

---

## 🔍 Current Hypotheses

### Hypothesis 1: asyncpg Pool Lifecycle Issue ⭐ LIKELY
**Theory:** asyncpg pool is somehow detecting loop closure even though we're not explicitly closing loops

**Evidence:**
- Pool object exists but marked as closed
- Pool tied to main application event loop
- Worker loops may be affecting main loop

**Next Steps:**
- Investigate asyncpg's event loop detection mechanism
- Check if `asyncio.set_event_loop(None)` triggers cleanup
- Consider pool recreation strategy

---

### Hypothesis 2: Hidden Loop Closure ⭐ POSSIBLE
**Theory:** There's another location closing loops we haven't found

**Evidence:**
- All three identified locations fixed
- Problem persists

**Next Steps:**
- Full codebase search for ALL loop-related calls:
  ```bash
  grep -r "\.close()" backend/src/ | grep -i loop
  grep -r "asyncio\.run\(" backend/src/
  grep -r "run_until_complete" backend/src/
  ```

---

### Hypothesis 3: Pool Created in Wrong Context ⭐ POSSIBLE
**Theory:** Pool initialized in startup event loop, inaccessible from worker loops

**Evidence:**
- Pool created during FastAPI startup
- Blog generation runs in separate thread/loop

**Next Steps:**
- Review pool initialization timing
- Consider lazy initialization per event loop
- Investigate asyncpg's thread-safety guarantees

---

### Hypothesis 4: Connection Leak ⭐ LESS LIKELY
**Theory:** Connections not returned to pool, causing pool to close

**Evidence:**
- Using context managers (`async with db_service.get_connection()`)
- Should auto-release connections

**Next Steps:**
- Add connection tracking
- Monitor in_use count during generation
- Check for exception handling gaps

---

## 📊 Monitoring Tools Created

### 1. Real-Time Pool Monitoring
```bash
watch -n 2 'curl -s -k https://localhost:5000/health/database-pool | jq ".stats"'
```

### 2. Log Monitoring
```bash
tail -f backend/backend.log | grep -E "Blog generation|Pool|closed|Instance"
```

### 3. Connection Tracking Script
**File:** `backend/monitor_pool_connections.sh`

### 4. Dashboard Monitoring
**URL:** `https://localhost:3001/admin/monitoring`
- Real-time graphs
- Connection pool stats
- Auto-refresh every 10 seconds

---

## 📚 Documentation Created

### 1. DB_POOL_CONNECTION_ANALYSIS.md
- Initial investigation findings
- Hypothesis development
- Early debugging steps

### 2. DB_POOL_DEFENSIVE_FIX_SUMMARY.md
- First fix attempt (line 261)
- Defensive pool recreation logic
- Initial test results

### 3. DB_POOL_ROOT_CAUSE_FIX.md (1800+ lines)
- Complete root cause analysis
- All three culprits identified
- Python asyncio.run() documentation
- Detailed code changes

### 4. DB_POOL_TESTING_GUIDE.md
- E2E testing procedures
- Success criteria
- Monitoring commands
- Expected vs actual behavior

### 5. DB_POOL_CLOSURE_INVESTIGATION_SUMMARY.md (THIS DOCUMENT)
- Complete investigation timeline
- All fixes attempted
- Current status and hypotheses
- Next steps for new investigation

---

## 🚨 Critical Questions Remaining

### Question 1: Event Loop Relationship
**Q:** How does asyncpg pool detect which event loop it belongs to?  
**Why it matters:** If pool is tied to specific loop, worker loops may not access it

### Question 2: asyncio.set_event_loop(None) Impact
**Q:** Does clearing event loop reference trigger cleanup in asyncpg?  
**Why it matters:** Our "safe" pattern may still be problematic

### Question 3: Thread Safety
**Q:** Is asyncpg pool thread-safe for our multi-threading approach?  
**Why it matters:** Blog generation runs in separate threads

### Question 4: Pool Initialization Context
**Q:** In which event loop is the pool initialized?  
**Why it matters:** May need pool per event loop or different architecture

### Question 5: Garbage Collection
**Q:** Are unclosed worker loops being garbage collected and triggering pool closure?  
**Why it matters:** GC may close loops we think are "safe"

---

## 🎯 Recommended Next Steps for New Investigation

### Step 1: Deep Dive into asyncpg Source Code
**Goal:** Understand how asyncpg tracks event loop lifecycle

**Actions:**
- Review `asyncpg.pool.Pool` implementation
- Find `_closed` flag setting logic
- Identify event loop detection mechanism
- Check for any automatic cleanup triggers

---

### Step 2: Comprehensive Loop Audit
**Goal:** Find ALL locations that might close loops

**Actions:**
```bash
# Search entire codebase
cd backend/src
grep -r "\.close()" . | grep -v ".pyc" | grep -v "__pycache__"
grep -r "asyncio\.run" . | grep -v ".pyc" | grep -v "__pycache__"
grep -r "run_until_complete" . | grep -v ".pyc" | grep -v "__pycache__"
grep -r "new_event_loop" . | grep -v ".pyc" | grep -v "__pycache__"
```

---

### Step 3: Alternative Architecture Exploration
**Goal:** Consider fundamentally different approaches

**Options:**

#### Option A: Pool Per Event Loop
Create separate pool for each worker event loop
```python
# Thread-local pool storage
_thread_local_pools = threading.local()

def get_pool_for_current_loop():
    loop = asyncio.get_event_loop()
    if not hasattr(_thread_local_pools, 'pool'):
        _thread_local_pools.pool = await asyncpg.create_pool(...)
    return _thread_local_pools.pool
```

#### Option B: Synchronous Connection Pattern
Avoid async pools entirely, use sync connections
```python
# Single synchronous connection per blog generation
conn = psycopg2.connect(...)
try:
    # Do work
finally:
    conn.close()
```

#### Option C: Pool Recreation Strategy
Accept pool closure, recreate on each blog
```python
async def ensure_fresh_pool():
    if db_service.is_pool_closed():
        await db_service.close()  # Clean up old
        await db_service.initialize()  # Create new
```

#### Option D: Remove Multi-Threading
Run blog generation in main event loop
```python
# Instead of threading:
result = await self.crew.kickoff_async(inputs=inputs)
# No separate event loops needed
```

---

### Step 4: Detailed Instrumentation
**Goal:** Track exact moment pool closes

**Actions:**
1. Add logging to asyncpg pool close detection
2. Capture stack trace when `_closed` changes to `True`
3. Monitor pool state before/during/after each flow phase
4. Track all event loop creations and destructions

**Code to Add:**
```python
# In database_service.py
def get_pool_stats(self):
    stats = super().get_pool_stats()
    
    # Capture stack if pool just closed
    is_closed = stats['closed']
    if is_closed and not self._last_known_closed_state:
        import traceback
        logger.error("🚨 POOL JUST CLOSED! Stack trace:")
        logger.error(traceback.format_stack())
    
    self._last_known_closed_state = is_closed
    return stats
```

---

### Step 5: Minimal Reproduction Case
**Goal:** Isolate problem in smallest possible code

**Actions:**
Create standalone script that reproduces issue:
```python
# test_pool_closure.py
import asyncio
import asyncpg

async def main():
    # Create pool
    pool = await asyncpg.create_pool(...)
    print(f"Pool closed: {pool._closed}")
    
    # Simulate blog generation pattern
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    try:
        result = new_loop.run_until_complete(some_async_work())
    finally:
        asyncio.set_event_loop(None)
    
    # Check pool status
    print(f"Pool closed after: {pool._closed}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📋 Files to Review in New Investigation

### Critical Files
1. `backend/src/bloggen/flows.py` - Lines 235-295 (blog generation with event loops)
2. `backend/src/core/database_service.py` - Entire file (pool management)
3. `backend/src/main.py` - Startup and pool initialization
4. `backend/src/api.py` - API endpoints that trigger blog generation

### Supporting Files
5. `backend/src/bloggen/tools_manager.py` - Tools that use database
6. `backend/src/core/config.py` - Configuration
7. `backend/requirements.txt` - Check asyncpg version

### Log Files
8. `backend/backend.log` - Current runtime logs
9. `backend/logs/` - CrewAI logs

---

## 🔧 Current System State

### Backend
- **Process:** PID 739376
- **Status:** Running
- **Port:** 5000 (HTTPS)
- **Pool Status:** `closed=false` (until first blog)
- **Code Version:** All fixes applied (lines 261, 279, 282)

### Frontend
- **Process:** PID 380435
- **Status:** Running
- **Port:** 3001 (HTTPS)
- **Monitoring Dashboard:** `https://localhost:3001/admin/monitoring`

### Database
- **Type:** PostgreSQL
- **Pool Config:** min=2, max=20 connections
- **Status:** Database itself is healthy (verified)

---

## ⚠️ Known Working Workarounds

### Workaround 1: Restart Backend Per Blog
```bash
# After each blog generation:
pkill -f "python src/main.py"
cd backend && source .venv/bin/activate && python src/main.py &
```
**Downside:** Not practical for production

### Workaround 2: Pool Recreation
```python
# In API endpoint before blog generation:
await db_service.close()
await db_service.initialize()
```
**Downside:** Performance overhead, connection churn

---

## 🎓 Key Learnings

### 1. Python asyncio Behavior
- `asyncio.run()` ALWAYS closes the loop it creates
- Event loops should not be closed if shared resources depend on them
- `asyncio.set_event_loop(None)` clears reference but doesn't close
- Worker loops and main loops are separate entities

### 2. asyncpg Pool Behavior
- Pools are tied to event loops
- Pool `_closed` flag set to `True` when associated loop closes
- No automatic pool recovery mechanism
- Context managers handle connection return, not pool lifecycle

### 3. FastAPI + asyncpg Integration
- Pool typically initialized during app startup
- Startup uses main application event loop
- Background tasks may run in different loop contexts
- Thread-based execution adds complexity

### 4. Debugging Async Issues
- Stack traces crucial for understanding call context
- Object ID tracking helps verify singleton behavior
- Logging event loop IDs shows context switches
- Real-time monitoring reveals exact failure timing

---

## 📞 Summary for Context

**Problem:** Database pool closes after first blog generation, preventing subsequent blogs.

**Root Cause Attempts:**
1. ✅ Fixed `_closed` default value bug - **Didn't solve it**
2. ✅ Removed `new_loop.close()` line 261 - **Didn't solve it**
3. ✅ Replaced `asyncio.run()` lines 279, 282 - **Didn't solve it**
4. ✅ Restarted backend with fresh code - **Didn't solve it**

**Current Status:** 
- All identified event loop closures removed
- Code verified in running process
- Pool still closes after first blog
- **Issue persists despite comprehensive fixes**

**Most Likely Next Direction:**
1. Deep dive into asyncpg source code to understand pool-loop binding
2. Consider alternative architecture (pool per loop, sync connections, or single-threaded)
3. Create minimal reproduction case outside of application context
4. Add detailed instrumentation to catch exact closure moment

**Critical Insight:**
The problem is NOT simply about explicit loop closures we can find and remove. It's about the fundamental **relationship between asyncpg pools and event loops** in a multi-threaded, multi-loop environment.

---

## 📎 Appendix: Verification Commands

### Check Current Backend Process
```bash
ps aux | grep "python src/main.py" | grep -v grep
```

### Verify Fixes in Code
```bash
grep -A5 -B5 "asyncio.run\|loop.close" backend/src/bloggen/flows.py | head -30
```

### Test Pool Health
```bash
curl -s -k https://localhost:5000/health/database-pool | jq '.'
```

### Monitor Pool in Real-Time
```bash
watch -n 2 'curl -s -k https://localhost:5000/health/database-pool | jq ".stats"'
```

### View Recent Logs
```bash
tail -100 backend/backend.log | grep -E "Blog|Pool|Instance|closed"
```

### Check asyncpg Version
```bash
cd backend && source .venv/bin/activate && pip show asyncpg
```

---

**End of Summary - October 14, 2025**

*This document contains the complete history of investigation attempts. The problem remains unresolved and requires deeper architectural analysis or alternative approach.*
