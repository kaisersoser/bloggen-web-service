# Debug Testing Guide - Agent Flow Visualization

## 🔍 Testing Session Preparation

**Date**: October 21, 2025  
**Goal**: Identify why nodes aren't generating dynamically  
**Approach**: Comprehensive console logging throughout SSE → Graph pipeline

---

## ✅ Servers Running

### Backend (Flask + CrewAI)
- **URL**: `https://localhost:5000`
- **Status**: ✅ Running (Process ID: 296644)
- **Features**: Database pool, Redis, LLM interceptor, S3 cleanup all initialized

### Frontend (Next.js)  
- **URL**: `https://localhost:3001`
- **Status**: ✅ Running (Process ID: 301616)
- **Mode**: HTTPS development mode with hot reload

---

## 🧪 Testing Steps

### Step 1: Open Browser DevTools
1. Navigate to `https://localhost:3001`
2. Open DevTools (F12 or Right-click → Inspect)
3. Go to **Console** tab
4. Clear console (click trash icon)
5. Keep console visible throughout test

---

### Step 2: Start Blog Generation
1. Sign in with Google/GitHub
2. Enter a simple topic: **"The future of AI"**
3. Click **"Generate Blog"** button
4. **Immediately switch to Visual Flow tab**

---

### Step 3: Monitor Console Output

Look for these log messages in order:

#### Phase 1: SSE Connection
```
🟢 [useWorkflowSSE] SSE Connection OPEN for taskId: task_xxxxx
```
✅ **Expected**: Connection establishes within 1-2 seconds  
❌ **If missing**: SSE connection failed

---

#### Phase 2: Event Reception
```
📨 [useWorkflowSSE] RAW SSE EVENT: {"type":"status",...}
📦 [useWorkflowSSE] PARSED DATA: {type: "status", data: {...}}
🔄 [useWorkflowSSE] TRANSFORMED EVENT: {type: "status", data: {...}}
✅ [useWorkflowSSE] Calling onEvent callback with: status
```
✅ **Expected**: Events arrive every 1-3 seconds  
❌ **If missing**: Backend not emitting events OR transformation failed

---

#### Phase 3: Graph Builder Processing
```
🎬 [GraphBuilder] ===== Processing SSE Event =====
🎬 [GraphBuilder] Event Type: status
🎬 [GraphBuilder] Event Data: { task_id: "...", step: "Step 1/5", ... }
➡️ [GraphBuilder] Routing to handleStatusEvent
📊 [handleStatusEvent] Processing status event: {...}
✅ [handleStatusEvent] Phase node created/updated: phase-research
✅ [GraphBuilder] After processing: { nodeCount: 1, edgeCount: 0, nodesArray: ["phase-research"] }
```
✅ **Expected**: Node count increases with each event  
❌ **If missing**: Graph builder not creating nodes

---

#### Phase 4: React State Update
```
🎨 [WorkflowGraph] handleSSEEvent called with: status
🎨 [WorkflowGraph] Updated graph from builder: { nodeCount: 1, edgeCount: 0, currentPhase: "Research" }
🎨 [WorkflowGraph] setGraph called, React should re-render
📈 [WorkflowGraph] Graph state updated: { nodeCount: 1, nodes: [{id: "phase-research", ...}] }
```
✅ **Expected**: React state updates trigger re-renders  
❌ **If missing**: React not updating OR component unmounted

---

### Step 4: Visual Verification

**What you should see in the workflow graph:**

1. **Initialization Panel** (top-center):
   - Shows "Initializing..." → "Research" → "Content Generation" etc.
   - Progress bar fills from 0% → 100%
   - Connection status: **●Live** (green dot)

2. **Phase Nodes** (horizontal layout):
   - Gray border → Blue pulsing border (in_progress) → Green border (completed)
   - Progress bars animate
   - Nodes appear left to right

3. **Agent Nodes** (below phases):
   - Brain icon with agent name
   - Purple color scheme
   - Expandable reasoning section

4. **Tool Nodes** (below agents):
   - Tool-specific icons (Search, Image, Globe)
   - Status badges (Running, Success, Failed)
   - Orange/blue color scheme

5. **Debug Panel** (bottom-left):
   ```
   Nodes: 5
   Edges: 4
   Active: agent-researcher-1
   Phase: Research
   ```

---

## 🐛 Common Issues & Diagnosis

### Issue 1: No SSE Connection
**Symptom**: No `🟢 [useWorkflowSSE] SSE Connection OPEN` message

**Possible Causes**:
- JWT token not retrieved
- Backend stream endpoint unreachable
- CORS issue

**Check**:
```javascript
// In console, run:
fetch('/api/auth/jwt-token').then(r => r.json()).then(console.log)
// Should return: {token: "eyJ..."}
```

---

### Issue 2: Events Arrive But No Transformation
**Symptom**: See `📨 RAW SSE EVENT` but no `🔄 TRANSFORMED EVENT`

**Possible Causes**:
- Event format mismatch
- `transformSSEEvent()` function failing

**Check Console For**:
```
🔍 [transformSSEEvent] Input rawData: {...}
🏷️ [transformSSEEvent] Message type detected: <type>
```

**Look at raw event structure** - does it have `message_type` or `type` field?

---

### Issue 3: Events Transformed But No Nodes
**Symptom**: See `✅ Calling onEvent callback` but no `🎬 [GraphBuilder]` messages

**Possible Causes**:
- `handleSSEEvent` callback not wired correctly
- Graph builder not receiving events

**Check**:
- Is `handleSSEEvent` being called?
- Is `graphBuilder.current.processSSEEvent()` throwing error?

---

### Issue 4: Nodes Created But Not Visible
**Symptom**: See `✅ Phase node created` and `nodeCount: 1` but graph empty

**Possible Causes**:
- ReactFlow not rendering
- Dagre layout issue
- CSS hiding nodes

**Check React DevTools**:
1. Open React DevTools tab
2. Find `WorkflowGraph` component
3. Inspect `graph` state prop
4. Verify `nodes` array has entries
5. Check if `layoutedNodes` has positions

---

### Issue 5: Tab Switching Resets Graph
**Symptom**: Nodes appear, then disappear when switching tabs

**Diagnosis**:
```
🔄 [WorkflowGraph] TaskId changed, resetting graph: task_xxxxx
```

**This is the KNOWN ISSUE** - component remounts on tab switch.  
**Solution**: Phase 3 implementation (inline workflow design)

---

## 📋 Debugging Checklist

Run through this checklist during test:

- [ ] Browser console open and visible
- [ ] Console cleared before starting generation
- [ ] Signed in successfully
- [ ] Topic entered and Generate clicked
- [ ] Switched to Visual Flow tab immediately
- [ ] See `🟢 SSE Connection OPEN` message
- [ ] See `📨 RAW SSE EVENT` messages arriving
- [ ] See `🔄 TRANSFORMED EVENT` messages
- [ ] See `🎬 [GraphBuilder]` processing messages
- [ ] See `nodeCount` increasing in logs
- [ ] See `📈 Graph state updated` messages
- [ ] See debug panel showing node count
- [ ] See actual nodes rendered in graph

---

## 📊 Expected Console Output (Sample)

Here's what a **successful** test should look like:

```
🟢 [useWorkflowSSE] SSE Connection OPEN for taskId: task_20251021_175630_abc123
🔄 [WorkflowGraph] TaskId changed, resetting graph: task_20251021_175630_abc123
📈 [WorkflowGraph] Graph state updated: { nodeCount: 0, nodes: [] }

📨 [useWorkflowSSE] RAW SSE EVENT: {"type":"status","data":{"task_id":"task_xxx","status":"initializing",...}}
📦 [useWorkflowSSE] PARSED DATA: {type: "status", ...}
🔄 [useWorkflowSSE] TRANSFORMED EVENT: {type: "status", data: {...}}
✅ [useWorkflowSSE] Calling onEvent callback with: status

🎨 [WorkflowGraph] handleSSEEvent called with: status
🎬 [GraphBuilder] ===== Processing SSE Event =====
🎬 [GraphBuilder] Event Type: status
➡️ [GraphBuilder] Routing to handleStatusEvent
📊 [handleStatusEvent] Processing status event: {...}
✅ [handleStatusEvent] Phase node created/updated: phase-research
✅ [GraphBuilder] After processing: { nodeCount: 1, nodesArray: ["phase-research"] }
🎨 [WorkflowGraph] Updated graph from builder: { nodeCount: 1, edgeCount: 0 }
🎨 [WorkflowGraph] setGraph called, React should re-render
📈 [WorkflowGraph] Graph state updated: { nodeCount: 1, nodes: [{id: "phase-research", type: "phase", ...}] }

(Repeat for each event: agent_thinking, tool_usage, etc.)
```

---

## 🚨 What to Capture

### If Test Fails, Save:
1. **Full console log** (right-click console → Save as...)
2. **Screenshot of Visual Flow tab**
3. **Screenshot of Console tab messages**
4. **React DevTools snapshot** of WorkflowGraph component state
5. **Network tab** showing SSE stream connection

### Key Questions to Answer:
1. Did SSE connection establish? (green Live indicator)
2. Are events arriving? (see 📨 RAW SSE EVENT logs)
3. Are events transforming? (see 🔄 TRANSFORMED EVENT logs)
4. Is graph builder creating nodes? (see nodeCount increasing)
5. Is React updating state? (see 📈 Graph state updated logs)
6. Are nodes rendering? (see visual nodes in graph)

---

## ⏭️ Next Steps Based on Results

### Scenario A: No SSE Connection
→ Fix authentication/connection issue  
→ Check backend stream endpoint  
→ Verify JWT token retrieval

### Scenario B: Events Arrive But Don't Transform
→ Fix `transformSSEEvent()` function  
→ Update event type mapping  
→ Handle backend event format

### Scenario C: Events Transform But No Nodes
→ Debug graph builder handlers  
→ Check node creation logic  
→ Verify state management

### Scenario D: Nodes Created But Not Visible
→ Debug ReactFlow rendering  
→ Check Dagre layout  
→ Inspect CSS/styling

### Scenario E: Everything Works!
→ Document findings  
→ Proceed to Phase 3 (inline workflow design)  
→ Remove tab-based interface

---

**Ready to test!** Open browser, follow steps above, and capture all console output.
