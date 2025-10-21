# Agent Flow Visualization - REVISED Implementation Plan

_Created: October 21, 2025_  
_Based on: Initial testing feedback and UX redesign_

---

## 🔴 Critical Issues Identified (Testing Phase)

### Issue 1: Tab Switching Causes ReactFlow Reset
**Problem**: Each tab switch remounts the WorkflowGraph component, breaking SSE connection and losing graph state.

**Root Cause**: React unmounts components when tab content is hidden, triggering useEffect cleanup.

**Impact**: User cannot switch between Console and Visual Flow without losing workflow progress.

---

### Issue 2: Nodes Not Generating Dynamically
**Problem**: Graph nodes don't appear in real-time as SSE events arrive.

**Potential Causes**:
- SSE event transformation not mapping correctly to graph builder
- Graph builder not processing events properly
- ReactFlow not re-rendering on state updates
- Backend events not matching expected format

**Requires**: Debugging SSE event flow and graph builder logic.

---

### Issue 3: Console View Dependency
**Problem**: Current tabbed design requires console view alongside workflow, creating UX confusion.

**User Feedback**: Console view should be retired in favor of Agent Flow as primary visualization.

---

## 🎨 New Design Vision

### Current Flow (Tab-Based) ❌
```
┌─────────────────────────────────────────┐
│ [Instructions] [Console] [Visual Flow] │ ← Tabs cause remounting
├─────────────────────────────────────────┤
│                                         │
│  Tab content (one visible at a time)   │
│                                         │
└─────────────────────────────────────────┘
```

### Revised Flow (Inline Workflow) ✅
```
BEFORE GENERATION:
┌─────────────────────────────────────────┐
│ ┌─────────────────────────────────────┐ │
│ │  📝 Instructions Panel              │ │
│ │  - Topic input                      │ │
│ │  - Additional instructions          │ │
│ │  - Generate button                  │ │
│ │                                     │ │
│ │  (Full height, centered)            │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘

DURING/AFTER GENERATION:
┌─────────────────────────────────────────┐
│ ╔═══════════════════════════════════════╗ │
│ ║ 📝 AI Blog Generation in Progress... ║ │ ← Minimized instruction bar
│ ╚═══════════════════════════════════════╝ │
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │  🔄 Agent Flow Visualization        │ │
│ │  ┌───┐   ┌───┐   ┌───┐   ┌───┐    │ │
│ │  │ R │──▶│ C │──▶│ F │──▶│ E │    │ │ ← Live workflow graph
│ │  └───┘   └───┘   └───┘   └───┘    │ │
│ │  (Real-time node updates)           │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [< Back to Edit] [Console Logs ▼]      │ ← Optional collapsed console
└─────────────────────────────────────────┘
```

---

## 📋 Revised Roadmap

### ✅ Phase 1: Foundation (COMPLETE)
- [x] Type definitions (WorkflowNode, WorkflowEdge, WorkflowGraph)
- [x] WorkflowGraphBuilder class
- [x] Basic WorkflowGraph component with ReactFlow
- [x] Custom node components (PhaseNode, AgentNode, ToolNode)
- [x] Dependencies: reactflow, dagre, framer-motion

**Status**: ✅ All infrastructure in place, needs debugging

---

### 🔴 Phase 2: Critical Fixes (URGENT - THIS MILESTONE)
**Goal**: Fix current implementation before proceeding with new design

#### Task 2.1: Debug SSE Event Flow ⚠️ HIGH PRIORITY
**Problem**: Nodes not appearing dynamically

**Action Items**:
- [ ] Add comprehensive logging to `useWorkflowSSE` hook
- [ ] Verify backend SSE events match expected format
- [ ] Test `transformSSEEvent()` function with real event data
- [ ] Add browser console debugging for incoming SSE messages
- [ ] Verify JWT token authentication in SSE connection

**Acceptance Criteria**:
- Console logs show incoming SSE events in real-time
- `transformSSEEvent()` correctly maps backend → graph format
- SSE connection status shows "Live" (green dot)

---

#### Task 2.2: Debug Graph Builder Logic ⚠️ HIGH PRIORITY
**Problem**: Events received but nodes not created

**Action Items**:
- [ ] Add debug logging to `WorkflowGraphBuilder.processSSEEvent()`
- [ ] Verify each handler: `handleStatusEvent`, `handleAgentThinkingEvent`, `handleToolUsageEvent`
- [ ] Test phase parsing: "Step 2/5" → "Research" phase mapping
- [ ] Verify node creation and state updates
- [ ] Check ReactFlow re-render triggers

**Acceptance Criteria**:
- Graph builder creates nodes for each event type
- Nodes array updates in React state
- ReactFlow re-renders when state changes
- Debug panel shows correct node/edge counts

---

#### Task 2.3: Fix Graph State Persistence ⚠️ MEDIUM PRIORITY
**Problem**: Need to preserve graph state during view changes

**Action Items**:
- [ ] Move graph state up to parent component (page.tsx)
- [ ] Use React Context or state management for workflow data
- [ ] Ensure WorkflowGraph doesn't unmount during transitions
- [ ] Implement proper cleanup only on generation completion

**Acceptance Criteria**:
- Graph state persists across UI changes
- SSE connection remains active throughout generation
- No unnecessary remounting of WorkflowGraph

---

### 🎨 Phase 3: New UX Implementation (NEXT MILESTONE)
**Goal**: Implement inline workflow design

#### Task 3.1: Create Collapsible Instructions Panel
**New Component**: `CollapsiblePromptBar.tsx`

**Features**:
- **Expanded state** (before generation): Full prompt form
- **Collapsed state** (during generation): Horizontal bar with:
  - Topic/title display
  - Progress indicator (0-100%)
  - Current phase name
  - "Edit" button to re-expand
  - "Stop Generation" button

**Acceptance Criteria**:
- Smooth animation between expanded/collapsed states
- Collapsed bar shows real-time progress
- User can re-expand to edit (with confirmation dialog if generation active)

---

#### Task 3.2: Integrate Workflow into Main Page Layout
**Modified Component**: `src/app/blog/page.tsx`

**Changes**:
- Remove `TabbedPromptInterface` component
- Add `CollapsiblePromptBar` at top
- Add `WorkflowGraph` directly below (always mounted)
- Move console logs to collapsible drawer at bottom

**Layout Structure**:
```tsx
<div className="blog-page">
  <Header />
  <CollapsiblePromptBar 
    expanded={!isGenerating}
    onSubmit={handleGenerateBlog}
    currentJob={currentJob}
  />
  {currentJobId && (
    <WorkflowGraph 
      taskId={currentJobId}
      className="flex-1 min-h-[500px]"
    />
  )}
  <CollapsibleConsoleDrawer logs={taskLogs} />
  <BlogTileGrid blogs={previousBlogs} />
</div>
```

**Acceptance Criteria**:
- Instructions collapse when generation starts
- Workflow appears immediately without tab switching
- No ReactFlow remounting during generation lifecycle
- Console logs accessible via bottom drawer (optional)

---

#### Task 3.3: Implement Console Drawer (Optional)
**New Component**: `ConsoleDrawer.tsx`

**Features**:
- Collapsed by default (show button with log count badge)
- Expands from bottom as overlay
- Shows same console output as before
- "Hide Console" button to collapse
- Positioned above workflow (z-index layering)

**Acceptance Criteria**:
- Drawer doesn't interfere with workflow view
- Smooth slide-up/down animation
- Maintains scroll position when toggled

---

### 🐛 Phase 4: Bug Fixes & Refinements (AFTER PHASE 3)

#### Task 4.1: Optimize ReactFlow Performance
- [ ] Implement node memoization (`React.memo`)
- [ ] Debounce rapid SSE events (e.g., content streaming)
- [ ] Optimize Dagre layout recalculations
- [ ] Add loading skeleton during initial graph build

#### Task 4.2: Enhance Node Interactivity
- [ ] Click phase node → Show draft preview modal
- [ ] Click agent node → Expand reasoning details
- [ ] Click tool node → Show full tool output
- [ ] Hover tooltips with additional metadata

#### Task 4.3: Add Workflow Controls
- [ ] Pause/Resume generation button
- [ ] Zoom to fit button
- [ ] Export graph as PNG/SVG
- [ ] Full-screen workflow mode

---

### 📱 Phase 5: Mobile Responsiveness (DEFERRED)

**Note**: Original Milestone 4 (mobile timeline view) is **deferred** until desktop experience is stable.

**When to implement**:
- After Phase 3 complete and desktop UX validated
- Consider vertical timeline for mobile (< 768px)
- Touch gesture support for node expansion
- Simplified layout for small screens

---

### ✅ Phase 6: Testing & Documentation (FINAL)

#### Task 6.1: Comprehensive Testing
- [ ] Unit tests for `WorkflowGraphBuilder` (80% coverage)
- [ ] Integration tests for SSE → Graph pipeline
- [ ] E2E tests for complete generation flow
- [ ] Performance testing (handle 100+ nodes)

#### Task 6.2: Documentation
- [ ] Update main README with workflow visualization
- [ ] Create user guide with screenshots
- [ ] Document SSE event → graph transformation
- [ ] Add troubleshooting section

---

## 🎯 Updated Timeline & Priorities

### Immediate Focus (This Week)
1. **Fix SSE event flow** (Task 2.1) - Debug why nodes don't appear
2. **Fix graph builder** (Task 2.2) - Ensure events create nodes correctly
3. **Fix state persistence** (Task 2.3) - Prevent remounting issues

### Next Sprint (Following Week)
4. **Implement new UX** (Phase 3) - Collapsible prompt + inline workflow
5. **Retire tab-based design** - Clean up old TabbedPromptInterface code
6. **Polish interactions** (Phase 4) - Click handlers, tooltips, controls

### Future Enhancements
7. **Mobile support** (Phase 5) - When desktop is stable
8. **Advanced features** - Export, search, replay mode
9. **Testing & docs** (Phase 6) - Before production release

---

## 🔍 Debugging Strategy (Phase 2 Focus)

### Step 1: Verify Backend SSE Events
**Test**: Monitor backend logs during generation
```bash
cd backend && tail -f logs/app.log
```

**Expected output**:
```
SSE: Emitting status event: {"type": "status", "step": "Step 1/5", ...}
SSE: Emitting agent_thinking: {"agent_name": "Senior Researcher", ...}
SSE: Emitting tool_usage: {"tool_name": "Serper Search", ...}
```

---

### Step 2: Verify Frontend SSE Reception
**Test**: Add console logs to `useWorkflowSSE.ts`
```typescript
eventSource.onmessage = (event) => {
  console.log('[useWorkflowSSE] RAW SSE:', event.data);
  const rawData = JSON.parse(event.data);
  console.log('[useWorkflowSSE] PARSED:', rawData);
  const transformedEvent = transformSSEEvent(rawData);
  console.log('[useWorkflowSSE] TRANSFORMED:', transformedEvent);
  // ...
};
```

**Expected console output**:
```
[useWorkflowSSE] RAW SSE: {"type":"status","data":{...}}
[useWorkflowSSE] PARSED: {type: "status", data: {...}}
[useWorkflowSSE] TRANSFORMED: {type: "status", data: {task_id: "...", ...}}
```

---

### Step 3: Verify Graph Builder Processing
**Test**: Add console logs to `WorkflowGraphBuilder`
```typescript
processSSEEvent(event: SSEEvent): WorkflowGraph {
  console.log('[GraphBuilder] Processing event:', event.type, event.data);
  
  switch (event.type) {
    case 'status':
      console.log('[GraphBuilder] Handling status event');
      return this.handleStatusEvent(event.data);
    // ...
  }
}
```

**Expected console output**:
```
[GraphBuilder] Processing event: status {task_id: "...", step: "Step 1/5"}
[GraphBuilder] Handling status event
[GraphBuilder] Created phase node: phase-research
```

---

### Step 4: Verify ReactFlow Rendering
**Test**: Check React DevTools for state updates
- Open React DevTools
- Find `WorkflowGraph` component
- Watch `graph` state object
- Verify `nodes` array updates when events arrive

**Expected state updates**:
```
graph: {
  nodes: [
    {id: "phase-research", type: "phase", status: "in_progress", ...}
  ],
  edges: [],
  activeNodeId: "phase-research"
}
```

---

## 📊 Success Metrics

### Phase 2 (Critical Fixes)
- [ ] SSE connection establishes (green "Live" indicator)
- [ ] Console shows incoming SSE events in real-time
- [ ] Graph builder creates nodes for each event
- [ ] Nodes array length increases during generation
- [ ] ReactFlow displays nodes visually
- [ ] Debug panel shows accurate node/edge counts

### Phase 3 (New UX)
- [ ] Instructions panel collapses smoothly when generation starts
- [ ] Workflow graph appears immediately (no tab switching)
- [ ] Graph remains visible and updating throughout generation
- [ ] No ReactFlow remounting during lifecycle
- [ ] Console drawer accessible but not obtrusive

### Phase 4+ (Refinements)
- [ ] Node click handlers show detailed information
- [ ] Animations are smooth (60fps)
- [ ] Performance handles 100+ nodes without lag
- [ ] Mobile layout adapts gracefully (deferred)

---

## 🚨 Risk Assessment

### High Risk
- **SSE event transformation mismatch**: Backend events may not match expected frontend format
- **ReactFlow state management**: Complex library with specific re-render requirements
- **Performance with many nodes**: Graph may slow down with 50+ nodes

### Medium Risk
- **Animation jank**: Heavy animations during rapid updates
- **Browser compatibility**: SSE EventSource support varies
- **State cleanup**: Memory leaks if cleanup not handled properly

### Low Risk
- **UI/UX polish**: Cosmetic issues that don't block functionality
- **Mobile responsiveness**: Deferred to later phase

---

## 📝 Next Steps (For Review)

### Questions for Decision:
1. **Console drawer vs complete removal**: Should we keep console logs accessible or fully retire them?
2. **Edit during generation**: Allow users to re-expand instructions during active generation?
3. **Multiple simultaneous generations**: Support queuing multiple blog generations?
4. **Graph persistence**: Should completed graphs remain visible after generation finishes?

### Immediate Action (After Approval):
1. Start with **Task 2.1**: Add debugging logs to SSE flow
2. Run test generation and capture console output
3. Identify exact point where event → node pipeline breaks
4. Fix root cause before proceeding to Phase 3

---

**Ready for review**. Please approve this revised plan or provide feedback before I proceed with debugging Phase 2.
