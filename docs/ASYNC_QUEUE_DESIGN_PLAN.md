# Asynchronous Blog Generation Queue - Design & Implementation Plan

**Date**: January 2025  
**Branch**: `prototype-agent-flow`  
**Status**: 📋 Design Phase  
**Complexity**: High (Multi-layer changes across frontend, backend, and database)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Proposed Architecture](#proposed-architecture)
4. [Detailed Design](#detailed-design)
5. [Implementation Phases](#implementation-phases)
6. [Technical Specifications](#technical-specifications)
7. [Database Schema Changes](#database-schema-changes)
8. [API Changes](#api-changes)
9. [Frontend Changes](#frontend-changes)
10. [Testing Strategy](#testing-strategy)
11. [Rollback Plan](#rollback-plan)
12. [Success Metrics](#success-metrics)

---

## Executive Summary

### Goal
Transform the blog generation system from a **synchronous blocking process** into a **fully asynchronous queue-based architecture** where users can submit multiple blog requests that are processed in the background with real-time status updates.

### Key Features
1. **Non-blocking submission**: Submit blog requests and continue using the UI
2. **Queue management**: Single-request-at-a-time processing with automatic queuing
3. **Real-time status**: Live updates showing "Generating", "Queued", "Published", or "Failed"
4. **Generation logs**: Streaming log viewer during generation (deleted after completion)
5. **Draft preview**: View partial blog drafts while generation is in progress
6. **Retry capability**: Regenerate failed blog requests with one click
7. **Multiple concurrent jobs**: User can have multiple blogs in various states

### User Experience Changes

#### Before (Current Synchronous System)
```
User enters prompt → UI blocks → Wait in Console tab... → Blog appears (or error)
- Logs displayed prominently in Console tab during generation
- User must wait on page to see completion
```

#### After (Async Queue System)
```
User enters prompt → Card appears immediately with "Generating" status
                   → User can submit MORE topics (they show as "Queued")
                   → Optional: Click "View Logs" button on card to see generation process
                   → When complete: "Generating" badge changes to "Published"
                   → "View Logs" button disappears after successful completion
                   → User can continue browsing/submitting while generation runs in background
```

### Key UX Improvements

1. **Immediate Feedback**: Blog card appears instantly with "Generating" status (not after completion)
2. **Hidden Logs by Default**: Console/logs only visible via button click on the generating blog card
3. **Multiple Submissions**: Users can queue multiple blog topics; queued items show "Queued" status
4. **Clean Completed State**: Published blogs show no generation controls (logs button removed)
5. **Async Freedom**: Users never blocked from submitting new requests

---

## Current State Analysis

### Current Architecture Flow

```
1. User submits blog topic in TabbedPromptInterface
2. Frontend calls POST /generate-blog with prompt
3. Backend creates task, starts background generation
4. Frontend connects SSE stream via /stream/<task_id>
5. Frontend shows Console tab with live logs
6. User MUST wait on page until generation completes
7. On completion, blog is saved and displayed
8. Logs are preserved in frontend state only
```

### Current Limitations

1. **UI Blocking**: User must stay on page and watch generation progress
2. **No Queue System**: Cannot submit multiple requests (one at a time)
3. **No Persistence**: Navigating away loses all progress/logs
4. **No Retry**: Failed blogs require manual re-submission
5. **No Draft Preview**: Cannot see partial content during generation
6. **Log Cleanup**: Logs are never cleaned up from backend storage
7. **Status Management**: Status states limited to in-memory job tracking

### Current Tech Stack

**Backend**:
- FastAPI with async/await
- PostgreSQL database (blogs table)
- Redis for pub/sub and SSE messaging
- Background tasks via `BackgroundTasks`
- Task manager with database persistence
- SSE streaming for real-time updates

**Frontend**:
- Next.js 14 with App Router
- React hooks for state management
- SSE connection via EventSource
- In-memory job state tracking
- TabbedPromptInterface for generation UI

**Database Schema (Current)**:
```sql
Table: blogs
- id (UUID, PK)
- userId (String, FK to users)
- topic (String)
- content (Text)
- status (QUEUED | IN_PROGRESS | COMPLETED | FAILED)
- progress (Int)
- currentStep (String)
- heroImageUrl (String?)
- instructions (String?)
- createdAt (DateTime)
- updatedAt (DateTime)
```

---

## Proposed Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          FRONTEND                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐       ┌──────────────────┐               │
│  │ Blog Generation  │       │  Blog Card Grid  │               │
│  │  Form/Interface  │       │   (All Blogs)    │               │
│  └────────┬─────────┘       └────────┬─────────┘               │
│           │ Submit                    │ Display                 │
│           ▼                           ▼                          │
│  ┌─────────────────────────────────────────────┐                │
│  │     Blog Queue Manager (React State)         │                │
│  │  - Active generation queue                   │                │
│  │  - Blog cards (Generating/Queued/Published)  │                │
│  │  - SSE connection management                 │                │
│  └─────────────────────────────────────────────┘                │
│           │                           ▲                          │
│           │ POST /queue-blog          │ SSE /stream/:id         │
│           │                           │                          │
└───────────┼───────────────────────────┼──────────────────────────┘
            │                           │
            ▼                           │
┌─────────────────────────────────────────────────────────────────┐
│                          BACKEND API                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  POST /queue-blog                  GET /stream/:task_id          │
│  ┌──────────────────┐              ┌──────────────────┐         │
│  │  1. Validate     │              │ 1. Auth check    │         │
│  │  2. Check queue  │              │ 2. Stream logs   │         │
│  │  3. Create blog  │              │ 3. Stream status │         │
│  │  4. Queue job    │              │ 4. Stream draft  │         │
│  └────────┬─────────┘              └──────────────────┘         │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────────────────────────────────┐                │
│  │       GENERATION QUEUE MANAGER               │                │
│  │  - Single worker processing loop             │                │
│  │  - FIFO queue (first in, first out)         │                │
│  │  - Status: queued → in_progress → complete   │                │
│  └─────────────────────────────────────────────┘                │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────────────────────────────────┐                │
│  │      BLOG GENERATION WORKER                  │                │
│  │  - Process one blog at a time                │                │
│  │  - Execute BlogGenerationFlow                │                │
│  │  - Publish SSE updates                       │                │
│  │  - Save drafts to Redis                      │                │
│  │  - Update database status                    │                │
│  └─────────────────────────────────────────────┘                │
│           │                                                       │
│           ▼                                                       │
└───────────┼───────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PERSISTENCE LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐       ┌──────────────────┐               │
│  │   PostgreSQL     │       │      Redis       │               │
│  │                  │       │                  │               │
│  │ - blogs table    │       │ - generation_logs│               │
│  │ - queue status   │       │ - draft_content  │               │
│  │ - retry state    │       │ - SSE pub/sub    │               │
│  └──────────────────┘       └──────────────────┘               │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Architectural Changes

#### 1. Queue Manager Service (New Backend Component)
- Singleton service managing blog generation queue
- FIFO processing: only one blog generated at a time
- Automatic queuing of new requests when worker is busy
- State machine: `queued → in_progress → completed/failed`

#### 2. Log Storage System (New Backend Component)
- **During generation**: Logs stored in Redis with TTL
- **After completion**: Logs automatically deleted (configured retention)
- **Structure**: `generation_logs:{task_id}` → List of log entries
- **API endpoint**: `GET /generation-logs/:task_id` (only during generation)

#### 3. Draft Content System (New Backend Component)
- **Progressive drafts**: Partial blog content saved to Redis as it's generated
- **Structure**: `draft_content:{task_id}` → JSON with sections
- **API endpoint**: `GET /draft/:task_id` (only during generation)
- **Auto-cleanup**: Deleted when blog moves to `COMPLETED` or `FAILED`

#### 4. Blog Card Component (Enhanced Frontend)
- **Status indicators**: Visual badges for Generating/Queued/Published/Failed
- **Action buttons**:
  - "View Logs" (only during generation)
  - "View Draft" (only during generation with partial content)
  - "Regenerate" (only for failed blogs)
  - "View Blog" (only for completed blogs)
  - "Delete" (always available)

#### 5. Generation Log Modal (New Frontend Component)
- Modal dialog showing streaming logs from backend
- Auto-scrolling console view
- Real-time updates via SSE connection
- Closes automatically when generation completes

#### 6. Draft Preview Modal (New Frontend Component)
- Modal showing partial blog content
- Sections appear as they're generated
- Visual indicator: "Draft - Generation in Progress"
- Refreshes automatically as new sections arrive

---

## Detailed Design

### State Machine Diagram

```
┌──────────────┐
│   QUEUED     │  ← New blog submission
└──────┬───────┘
       │
       │ Worker picks up job
       ▼
┌──────────────┐
│ IN_PROGRESS  │  ← Generation actively running
└──────┬───────┘
       │
       ├────────────────┐
       │                │
       ▼                ▼
┌──────────────┐  ┌──────────────┐
│  COMPLETED   │  │    FAILED    │
└──────────────┘  └──────┬───────┘
                         │
                         │ User clicks "Regenerate"
                         ▼
                  ┌──────────────┐
                  │   QUEUED     │  ← Back to queue
                  └──────────────┘
```

### Queue Processing Logic

```python
class GenerationQueueManager:
    """
    Manages the FIFO queue for blog generation.
    Ensures only one blog is processed at a time.
    """
    
    def __init__(self):
        self.current_job: Optional[str] = None  # task_id of job being processed
        self.processing_lock = asyncio.Lock()
    
    async def enqueue_blog(self, task_id: str, user_id: str, topic: str, instructions: str):
        """Add blog to queue"""
        # 1. Create blog record in database with status=QUEUED
        # 2. If no job is currently processing, start immediately
        # 3. Otherwise, blog stays in QUEUED state
        # 4. Return task_id to frontend
    
    async def start_next_job(self):
        """Process next queued blog (called after job completes)"""
        async with self.processing_lock:
            if self.current_job is not None:
                return  # Already processing
            
            # Find oldest QUEUED blog from database
            next_blog = await get_next_queued_blog()
            
            if next_blog:
                self.current_job = next_blog.id
                await self.process_blog(next_blog)
    
    async def process_blog(self, blog: Blog):
        """Execute blog generation"""
        try:
            # 1. Update status to IN_PROGRESS
            await update_blog_status(blog.id, "IN_PROGRESS")
            
            # 2. Execute BlogGenerationFlow
            result = await run_blog_generation(blog)
            
            # 3. Update status to COMPLETED
            await save_blog_result(blog.id, result)
            
            # 4. Cleanup logs and drafts
            await cleanup_temporary_data(blog.id)
            
        except Exception as e:
            # Update status to FAILED
            await update_blog_status(blog.id, "FAILED", error=str(e))
        
        finally:
            # Release current job
            self.current_job = None
            
            # Start next queued job
            await self.start_next_job()
```

### Log Management System

```python
class GenerationLogManager:
    """Manages generation logs with automatic cleanup"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.log_ttl = 300  # 5 minutes after generation completes
    
    async def append_log(self, task_id: str, log_entry: dict):
        """Add log entry to Redis"""
        key = f"generation_logs:{task_id}"
        await self.redis.rpush(key, json.dumps(log_entry))
        await self.redis.expire(key, 3600)  # 1 hour max TTL
    
    async def get_logs(self, task_id: str) -> List[dict]:
        """Retrieve all logs for task"""
        key = f"generation_logs:{task_id}"
        logs = await self.redis.lrange(key, 0, -1)
        return [json.loads(log) for log in logs]
    
    async def cleanup_logs(self, task_id: str, delay_seconds: int = 300):
        """Schedule log deletion after delay"""
        # Set shorter TTL so logs expire after blog completes
        key = f"generation_logs:{task_id}"
        await self.redis.expire(key, delay_seconds)
    
    async def stream_logs_sse(self, task_id: str):
        """Stream logs via SSE (for modal viewer)"""
        # Subscribe to Redis pub/sub for new logs
        # Yield existing logs first, then stream new ones
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"log_updates:{task_id}")
        
        # Send existing logs
        existing_logs = await self.get_logs(task_id)
        for log in existing_logs:
            yield f"data: {json.dumps(log)}\n\n"
        
        # Stream new logs as they arrive
        async for message in pubsub.listen():
            if message['type'] == 'message':
                yield f"data: {message['data']}\n\n"
```

### Draft Content System

```python
class DraftContentManager:
    """Manages partial blog drafts during generation"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def update_draft(self, task_id: str, section: str, content: str):
        """Update draft content for a specific section"""
        key = f"draft_content:{task_id}"
        draft = await self.get_draft(task_id) or {}
        draft[section] = content
        draft['updated_at'] = datetime.utcnow().isoformat()
        
        await self.redis.set(key, json.dumps(draft), ex=3600)  # 1 hour TTL
    
    async def get_draft(self, task_id: str) -> Optional[dict]:
        """Retrieve current draft"""
        key = f"draft_content:{task_id}"
        draft_json = await self.redis.get(key)
        return json.loads(draft_json) if draft_json else None
    
    async def cleanup_draft(self, task_id: str):
        """Delete draft when blog completes"""
        key = f"draft_content:{task_id}"
        await self.redis.delete(key)
```

---

## Implementation Phases

### Phase 1: Backend Queue Infrastructure (3-4 days)

**Goal**: Build the queue manager and worker system

#### Tasks:
1. **Create `GenerationQueueManager` class**
   - Location: `backend/src/core/generation_queue_manager.py`
   - Implements FIFO queue logic
   - Single worker processing with locking
   - Auto-start next job on completion

2. **Create `GenerationLogManager` class**
   - Location: `backend/src/core/generation_log_manager.py`
   - Redis-backed log storage
   - Automatic TTL management
   - SSE streaming endpoint

3. **Create `DraftContentManager` class**
   - Location: `backend/src/core/draft_content_manager.py`
   - Redis-backed draft storage
   - Section-based updates
   - Cleanup on completion

4. **Update `main.py` endpoints**
   - Rename `POST /generate-blog` → `POST /queue-blog`
   - Add `GET /generation-logs/:task_id`
   - Add `GET /draft/:task_id`
   - Add `POST /regenerate-blog/:task_id`

5. **Integrate queue manager into blog generation flow**
   - Modify `async_blog_generation()` to use queue manager
   - Add log publishing to Redis during generation
   - Add draft content updates during generation phases

6. **Testing**
   - Unit tests for queue manager
   - Integration tests for log streaming
   - Load tests with multiple queued blogs

**Files Modified**:
- `backend/src/main.py` (endpoints)
- `backend/src/core/task_manager.py` (queue integration)
- `backend/src/bloggen/flows.py` (log/draft publishing)

**Files Created**:
- `backend/src/core/generation_queue_manager.py`
- `backend/src/core/generation_log_manager.py`
- `backend/src/core/draft_content_manager.py`
- `backend/src/tests/test_queue_manager.py`

---

### Phase 2: Database Schema Updates (1 day)

**Goal**: Add retry state and queue position tracking

#### Schema Changes:

```prisma
model Blog {
  // ... existing fields ...
  
  // NEW FIELDS
  queuePosition      Int?      // Position in queue (null if not queued)
  retryCount         Int       @default(0)  // Number of retry attempts
  maxRetries         Int       @default(3)  // Maximum retry attempts
  failureReason      String?   // Error message for failed blogs
  lastRetryAt        DateTime? // Timestamp of last retry
  completedAt        DateTime? // When generation finished
  
  // Indexes for queue management
  @@index([status, createdAt])  // For finding next queued blog
  @@index([userId, status])     // For user's blog list
}
```

#### Migration Tasks:
1. Create Prisma migration
2. Run migration on development database
3. Update Prisma client types
4. Update backend Blog model interfaces

**Files Modified**:
- `frontend-nextjs/blog-generator-ui/prisma/schema.prisma`
- `backend/src/models.py` (if Python models exist)

**Migration Command**:
```bash
cd frontend-nextjs/blog-generator-ui
npx prisma migrate dev --name add_queue_fields
npx prisma generate
```

---

### Phase 3: Frontend Components (3-4 days)

**Goal**: Build the async UI with immediate card appearance and hidden logs

#### Component Structure:

```
src/components/blog/
├── BlogQueueCard.tsx              # Updated blog card with conditional "View Logs" button
├── QueueStatusBadge.tsx           # Status badge (Generating/Queued/Published/Failed)
├── GenerationLogModal.tsx         # Modal for viewing live logs (HIDDEN by default)
├── DraftPreviewModal.tsx          # Modal for viewing partial drafts
└── queue-components.ts            # Component exports
```

#### Tasks:

1. **Update `BlogQueueCard.tsx`** (Already created, needs refinement)
   ```tsx
   interface BlogQueueCardProps {
     blog: QueueBlogData;
     onViewLogs?: (taskId: string) => void;      // Only shown for IN_PROGRESS/FAILED
     onViewDraft?: (taskId: string) => void;     // Only shown for IN_PROGRESS
     onRetry?: (taskId: string) => void;         // Only shown for FAILED
     onDelete?: (taskId: string) => void;
     onViewContent?: (blog: QueueBlogData) => void;  // Only shown for COMPLETED
   }
   
   // Key UX Rules:
   // - "View Logs" button: ONLY visible for IN_PROGRESS or FAILED status
   // - "View Logs" button: HIDDEN for COMPLETED (published) blogs
   // - "View Logs" button: HIDDEN for QUEUED (not started yet) blogs
   // - Card appears IMMEDIATELY after submission with "Generating" status
   // - Status badge updates in real-time via SSE
   ```

2. **Update `QueueStatusBadge.tsx`** (Already created)
   ```tsx
   // Statuses:
   // - "Generating" (yellow spinner) = IN_PROGRESS
   // - "Queued #X" (blue clock) = QUEUED
   // - "Published" (green checkmark) = COMPLETED
   // - "Failed" (red X) = FAILED
   ```

3. **Update `GenerationLogModal.tsx`** (Already created)
   ```tsx
   interface GenerationLogModalProps {
     isOpen: boolean;           // Controlled by parent state
     onClose: () => void;       // User can close manually
     taskId: string;
     logs: GenerationLog[];     // Fetched by useGenerationLogs hook
     isLoading?: boolean;
     isLive?: boolean;          // Whether generation is still active
     onRefresh?: () => void;
   }
   
   // Features:
   // - Opens ONLY when user clicks "View Logs" button on card
   // - SSE connection for real-time updates
   // - Auto-scrolling console
   // - Download logs button
   // - NOT shown automatically during generation
   ```

4. **Update `DraftPreviewModal.tsx`** (Already created)
   ```tsx
   interface DraftPreviewModalProps {
     isOpen: boolean;
     onClose: () => void;
     taskId: string;
     draft: DraftContent | null;
     isLoading?: boolean;
     onRefresh?: () => void;
   }
   
   // Features:
   // - Opens when user clicks "View Draft" button (optional feature)
   // - Shows sections as they're generated
   // - Markdown preview vs raw view toggle
   // - Auto-refresh every 3 seconds during generation
   ```

5. **Update Main Blog Page (`page.tsx`)**
   - Remove synchronous Console tab/TabbedPromptInterface (keep prompt input only)
   - Blog card appears IMMEDIATELY after /generate-blog returns task_id
   - Submit button NEVER disabled (allow multiple queued submissions)
   - Show all blogs in single grid (no separate "Generating" section)
   - Modal state management for logs/draft viewers
   
   ```tsx
   // page.tsx structure
   export default function BlogGenerationPage() {
     const [blogs, setBlogs] = useState<QueueBlogData[]>([]);
     const [showLogsModal, setShowLogsModal] = useState(false);
     const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
     
     const handleSubmit = async (topic: string) => {
       // 1. Call POST /generate-blog
       const response = await blogService.generateBlog(topic);
       
       // 2. IMMEDIATELY add blog card to UI with "Generating" status
       const newBlog: QueueBlogData = {
         id: response.task_id,
         topic,
         status: 'IN_PROGRESS',  // NOT 'QUEUED' if first in queue
         progress: 0,
         // ... other fields
       };
       setBlogs(prev => [newBlog, ...prev]);
       
       // 3. Submit button stays enabled for next submission
     };
     
     const handleViewLogs = (taskId: string) => {
       setSelectedTaskId(taskId);
       setShowLogsModal(true);  // Open modal
     };
     
     return (
       <>
         <BlogSubmissionForm onSubmit={handleSubmit} />
         
         {/* All blogs in one grid */}
         <div className="blog-grid">
           {blogs.map(blog => (
             <BlogQueueCard
               key={blog.id}
               blog={blog}
               onViewLogs={blog.status === 'IN_PROGRESS' || blog.status === 'FAILED' ? handleViewLogs : undefined}
               onViewDraft={blog.status === 'IN_PROGRESS' ? handleViewDraft : undefined}
               onRetry={blog.status === 'FAILED' ? handleRetry : undefined}
               onDelete={handleDelete}
               onViewContent={blog.status === 'COMPLETED' ? handleViewContent : undefined}
             />
           ))}
         </div>
         
         {/* Logs modal - HIDDEN until user clicks "View Logs" */}
         <GenerationLogModal
           isOpen={showLogsModal}
           onClose={() => setShowLogsModal(false)}
           taskId={selectedTaskId!}
           logs={logs}
         />
       </>
     );
   }
   ```

6. **Update custom hooks** (Already created)
   - `useGenerationQueue.ts` - Auto-refresh queue status
   - `useGenerationLogs.ts` - Fetch logs on demand (not auto-start)
   - `useDraftContent.ts` - Fetch draft on demand

**Files Modified**:
- `src/app/blog/page.tsx` (major refactor - remove Console, add card grid)
- `src/components/blog/BlogQueueCard.tsx` (conditional button visibility)
- `src/types/blog.ts` (ensure status types match)

**Files Already Created** (Phase 3 complete):
- `src/components/blog/QueueStatusBadge.tsx` ✅
- `src/components/blog/BlogQueueCard.tsx` ✅
- `src/components/blog/GenerationLogModal.tsx` ✅
- `src/components/blog/DraftPreviewModal.tsx` ✅
- `src/hooks/useGenerationQueue.ts` ✅
- `src/hooks/useGenerationLogs.ts` ✅
- `src/hooks/useDraftContent.ts` ✅
- `src/lib/services/blog.ts` (queue methods added) ✅

**Remaining Work**:
- Integrate components into main blog page
- Remove/hide Console tab during generation
- Update blog submission flow to show card immediately
- Add conditional rendering for "View Logs" button based on status

---

### Phase 4: API Client Updates (1 day)

**Goal**: Update frontend services for new endpoints

#### Tasks:

1. **Update `blog.ts` service**
   ```typescript
   class BlogService {
     // NEW METHODS
     async queueBlog(topic: string, instructions?: string): Promise<{ task_id: string }>;
     async getGenerationLogs(taskId: string): Promise<LogEntry[]>;
     async getDraft(taskId: string): Promise<DraftContent | null>;
     async regenerateBlog(blogId: string): Promise<{ task_id: string }>;
     async getQueuePosition(blogId: string): Promise<number | null>;
     
     // MODIFIED METHODS
     async getUserBlogs(): Promise<BlogData[]>;  // Now includes all statuses
   }
   ```

2. **Create SSE streaming utilities**
   ```typescript
   // src/lib/services/sse-stream.ts
   export function createLogStream(taskId: string): EventSource;
   export function createStatusStream(taskId: string): EventSource;
   ```

**Files Modified**:
- `src/lib/services/blog.ts`

**Files Created**:
- `src/lib/services/sse-stream.ts`

---

### Phase 5: Integration & Testing (2-3 days)

**Goal**: End-to-end testing and polish

#### Tasks:

1. **Integration testing**
   - Submit multiple blogs simultaneously
   - Verify FIFO queue processing
   - Test log streaming during generation
   - Test draft preview during generation
   - Test retry functionality for failed blogs

2. **Error handling**
   - Network errors during generation
   - SSE connection failures
   - Queue overflow scenarios
   - Database errors

3. **UI polish**
   - Loading states
   - Error messages
   - Success notifications
   - Accessibility improvements

4. **Performance testing**
   - 10+ blogs in queue
   - Concurrent users
   - Memory usage during generation
   - Redis cleanup verification

5. **Documentation**
   - API documentation updates
   - Component usage examples
   - Deployment guide updates

**Files Created**:
- `backend/src/tests/test_queue_integration.py`
- `frontend-nextjs/blog-generator-ui/src/tests/queue-system.test.tsx`
- `docs/ASYNC_QUEUE_API.md`
- `docs/ASYNC_QUEUE_USAGE.md`

---

## Technical Specifications

### API Endpoints

#### New Endpoints

##### `POST /queue-blog`
**Description**: Submit blog generation request to queue

**Request**:
```json
{
  "topic": "The future of AI",
  "instructions": "Focus on practical applications"
}
```

**Response**:
```json
{
  "task_id": "uuid-here",
  "status": "queued",
  "queue_position": 2,
  "message": "Blog queued for generation"
}
```

##### `GET /generation-logs/:task_id`
**Description**: Get generation logs (only available during generation)

**Response**:
```json
{
  "logs": [
    {
      "timestamp": "2025-01-19T10:30:00Z",
      "step": "research",
      "message": "Gathering information...",
      "progress": 25
    }
  ],
  "status": "in_progress"
}
```

**Error** (if blog completed):
```json
{
  "error": "Logs no longer available",
  "message": "Generation logs are only available during active generation"
}
```

##### `GET /draft/:task_id`
**Description**: Get partial draft content

**Response**:
```json
{
  "draft": {
    "title": "The Future of AI",
    "sections": {
      "introduction": "AI is transforming...",
      "section1": "Machine learning has..."
    },
    "progress": 60,
    "updated_at": "2025-01-19T10:32:00Z"
  },
  "status": "in_progress"
}
```

##### `POST /regenerate-blog/:blog_id`
**Description**: Retry failed blog generation

**Response**:
```json
{
  "task_id": "new-uuid",
  "status": "queued",
  "retry_count": 1,
  "message": "Blog re-queued for generation"
}
```

**Error** (if max retries exceeded):
```json
{
  "error": "Max retries exceeded",
  "message": "This blog has been retried 3 times. Please create a new request."
}
```

##### `GET /queue-status`
**Description**: Get current queue status

**Response**:
```json
{
  "current_job": "uuid-of-current-blog",
  "queued_count": 3,
  "user_queued_count": 1,
  "estimated_wait_time_seconds": 450
}
```

#### Modified Endpoints

##### `GET /blogs` (Modified)
**Changes**: Now returns blogs with all statuses

**Response**:
```json
{
  "blogs": [
    {
      "id": "uuid",
      "topic": "AI Topic",
      "status": "IN_PROGRESS",
      "progress": 45,
      "queue_position": null,
      "has_draft": true,
      "created_at": "2025-01-19T10:30:00Z"
    },
    {
      "id": "uuid2",
      "status": "QUEUED",
      "queue_position": 2
    },
    {
      "id": "uuid3",
      "status": "COMPLETED"
    }
  ]
}
```

### SSE Streams

#### `/stream/:task_id` (Enhanced)
**New event types**:

```javascript
// Draft update event
{
  "event": "draft_update",
  "data": {
    "section": "introduction",
    "content": "...",
    "progress": 30
  }
}

// Queue position update
{
  "event": "queue_position",
  "data": {
    "position": 1,
    "estimated_wait": 300
  }
}

// Generation started (moved from queued to in_progress)
{
  "event": "generation_started",
  "data": {
    "started_at": "2025-01-19T10:35:00Z"
  }
}
```

---

## Database Schema Changes

### Prisma Schema Update

```prisma
model Blog {
  id                 String    @id @default(cuid())
  userId             String
  topic              String
  content            String?   @db.Text
  status             String    @default("QUEUED")  // QUEUED | IN_PROGRESS | COMPLETED | FAILED
  progress           Int       @default(0)
  currentStep        String    @default("Queued")
  heroImageUrl       String?
  instructions       String?   @db.Text
  createdAt          DateTime  @default(now())
  updatedAt          DateTime  @updatedAt
  
  // NEW QUEUE FIELDS
  queuePosition      Int?      // Position in queue (1 = next, null = not queued)
  retryCount         Int       @default(0)
  maxRetries         Int       @default(3)
  failureReason      String?   @db.Text
  lastRetryAt        DateTime?
  completedAt        DateTime? // When generation finished (success or failure)
  estimatedDuration  Int?      // Estimated seconds to complete (calculated)
  
  user               User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  
  // Indexes for efficient queue queries
  @@index([status, createdAt])           // Find next queued blog
  @@index([userId, status, createdAt])   // User's blogs by status
  @@index([queuePosition])               // Queue position lookups
}
```

### Migration Strategy

1. **Create migration**:
   ```bash
   npx prisma migrate dev --name add_async_queue_fields
   ```

2. **Handle existing data**:
   - All existing `IN_PROGRESS` blogs → set to `QUEUED`
   - All existing `COMPLETED` blogs → set `completedAt` to `updatedAt`
   - Set `retryCount = 0` for all existing blogs

3. **Verify migration**:
   ```bash
   npx prisma studio  # Visual inspection
   npx prisma db push # Sync with database
   ```

---

## Revised User Workflow

### Scenario: User Submits Multiple Blogs

**Step 1: First Blog Submission**
```
User enters "AI and healthcare" → Clicks Submit
↓
Blog card appears IMMEDIATELY with:
- Badge: "Generating" (yellow, spinning)
- Progress: 0%
- Buttons: [View Logs] [View Draft] [Cancel]
↓
User can submit another topic OR click "View Logs" to watch progress
```

**Step 2: Second Blog Submission (while first is generating)**
```
User enters "Blockchain in finance" → Clicks Submit
↓
Second blog card appears with:
- Badge: "Queued #1" (blue, clock icon)
- Estimated wait: "~3 min"
- Buttons: [Cancel]
- NO "View Logs" button (not generating yet)
↓
User can submit MORE topics OR navigate away
```

**Step 3: First Blog Completes**
```
First blog card updates:
- Badge changes: "Generating" → "Published" (green, checkmark)
- [View Logs] button DISAPPEARS
- [View Draft] button DISAPPEARS
- New button appears: [View Blog]
↓
Second blog card updates:
- Badge changes: "Queued #1" → "Generating" (starts processing)
- Progress bar appears: 0% → 10% → 20%...
- [View Logs] button APPEARS
```

**Step 4: User Clicks "View Logs" (Optional)**
```
User clicks [View Logs] on generating blog
↓
Modal opens showing:
- Real-time streaming logs
- Auto-scrolling console
- Progress indicator
- [Close] button
↓
User can close modal and continue browsing
Logs continue updating in background
```

### Scenario: Blog Generation Fails

**Step 1: Failure Occurs**
```
Blog card updates:
- Badge: "Failed" (red, X icon)
- Error message preview shown
- Retry count: "Retry 0 of 3"
↓
Buttons available:
- [View Logs] - to see what went wrong
- [Retry] - regenerate with same topic
- [Delete] - remove failed blog
```

**Step 2: User Clicks "View Logs"**
```
Modal opens showing:
- Full error logs
- Stack trace (if available)
- Last successful step
↓
User can diagnose issue
```

**Step 3: User Clicks "Retry"**
```
Failed blog card updates:
- Badge: "Generating" (starts again)
- Retry count: "Retry 1 of 3"
- Progress resets to 0%
↓
Blog goes through queue again
[View Logs] button available again
```

### Key Behavioral Rules

1. **Submit Button**: NEVER disabled - users can always queue new blogs
2. **Logs Visibility**: Hidden by default, shown only when user clicks "View Logs"
3. **View Logs Button**:
   - Appears: During generation (IN_PROGRESS) or after failure (FAILED)
   - Disappears: After successful completion (COMPLETED)
4. **Queue Display**: All blogs shown together (not separate sections), sorted by status/time
5. **Real-time Updates**: Blog cards update automatically via SSE without page refresh

---

## Frontend Changes

### Type Definitions

```typescript
// src/types/blog.ts

export type BlogStatus = 'QUEUED' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';

export interface BlogData {
  id: string;
  userId: string;
  topic: string;
  content?: string;
  status: BlogStatus;
  progress: number;
  currentStep: string;
  heroImageUrl?: string;
  instructions?: string;
  createdAt: string;
  updatedAt: string;
  
  // Queue fields
  queuePosition?: number;
  retryCount: number;
  maxRetries: number;
  failureReason?: string;
  lastRetryAt?: string;
  completedAt?: string;
  estimatedDuration?: number;
  
  // Computed fields
  hasDraft?: boolean;
  canRetry?: boolean;
}

export interface DraftContent {
  title?: string;
  sections: Record<string, string>;
  progress: number;
  updated_at: string;
}

export interface GenerationLog {
  timestamp: string;
  step: string;
  message: string;
  progress: number;
  level: 'info' | 'warning' | 'error';
}

export interface QueueStatus {
  current_job?: string;
  queued_count: number;
  user_queued_count: number;
  estimated_wait_time_seconds: number;
}
```

### Component Hierarchy

```
page.tsx (Blog Generation Page)
│
├─ BlogSubmissionForm
│  └─ Prompt input + Submit button (ALWAYS enabled - never blocks)
│
├─ QueueStatusBar (NEW - Optional)
│  └─ Shows: "Processing: 1 blog, Queued: 3 blogs"
│
└─ BlogCollection Grid (Updated)
   │
   ├─ BlogCard (status: IN_PROGRESS)
   │  ├─ Badge: "Generating" with spinner icon
   │  ├─ Progress bar (0-100%)
   │  ├─ Topic/title
   │  ├─ Timestamp: "Started 2 min ago"
   │  └─ Actions: [View Logs] [View Draft] [Cancel]
   │     └─ "View Logs" button ONLY visible during generation
   │
   ├─ BlogCard (status: QUEUED)
   │  ├─ Badge: "Queued" with queue position (#2)
   │  ├─ Topic/title
   │  ├─ Estimated wait time: "~5 min wait"
   │  └─ Actions: [Cancel]
   │     └─ NO "View Logs" button (not generating yet)
   │
   ├─ BlogCard (status: COMPLETED)
   │  ├─ Badge: "Published" (green checkmark)
   │  ├─ Hero image
   │  ├─ Topic/title
   │  ├─ Timestamp: "Published 1 hour ago"
   │  └─ Actions: [View Blog] [Delete]
   │     └─ NO "View Logs" button (generation complete)
   │
   └─ BlogCard (status: FAILED)
      ├─ Badge: "Failed" (red X)
      ├─ Error message preview
      ├─ Retry count: "Retry 1 of 3"
      └─ Actions: [View Logs] [Retry] [Delete]
         └─ "View Logs" button visible to debug failure

Modals (triggered by blog card buttons):
├─ GenerationLogModal (ONLY for IN_PROGRESS or FAILED blogs)
│  ├─ Opens when user clicks "View Logs" button on card
│  ├─ SSE connection to /generation-logs/:id
│  ├─ Auto-scrolling console with timestamps
│  ├─ Live updates during generation
│  └─ Closes automatically OR manually
│
└─ DraftPreviewModal (ONLY for IN_PROGRESS blogs)
   ├─ Opens when user clicks "View Draft" button on card
   ├─ Fetches draft from /draft/:id
   ├─ Shows partial markdown content
   └─ Refreshes every 3 seconds during generation
```

### Key UX Rules

1. **Blog Card Appears Immediately**: As soon as user submits, card appears with "Generating" status
2. **Logs Hidden by Default**: Console/logs NOT shown automatically - only via "View Logs" button
3. **View Logs Button Lifecycle**:
   - ✅ **Visible**: During IN_PROGRESS (generating)
   - ✅ **Visible**: On FAILED blogs (for debugging)
   - ❌ **Hidden**: On COMPLETED blogs (published successfully)
   - ❌ **Hidden**: On QUEUED blogs (not generating yet)
4. **Multiple Submissions**: Submit button ALWAYS enabled, new submissions go to queue
5. **Queue Status Badges**:
   - "Generating" (yellow, spinning) = IN_PROGRESS
   - "Queued #X" (blue, clock icon) = QUEUED
   - "Published" (green, checkmark) = COMPLETED
   - "Failed" (red, X icon) = FAILED

---

## Testing Strategy

### Backend Tests

#### Unit Tests

```python
# backend/src/tests/test_queue_manager.py

async def test_enqueue_blog():
    """Test adding blog to queue"""
    # Arrange
    queue = GenerationQueueManager()
    
    # Act
    task_id = await queue.enqueue_blog("user1", "Test topic", None)
    
    # Assert
    blog = await get_blog(task_id)
    assert blog.status == "QUEUED"
    assert blog.queuePosition == 1

async def test_single_worker_processing():
    """Test that only one blog is processed at a time"""
    # Enqueue 3 blogs
    task1 = await queue.enqueue_blog("user1", "Topic 1", None)
    task2 = await queue.enqueue_blog("user1", "Topic 2", None)
    task3 = await queue.enqueue_blog("user1", "Topic 3", None)
    
    # Verify only first blog is IN_PROGRESS
    await asyncio.sleep(1)  # Allow processing to start
    
    blog1 = await get_blog(task1)
    blog2 = await get_blog(task2)
    blog3 = await get_blog(task3)
    
    assert blog1.status == "IN_PROGRESS"
    assert blog2.status == "QUEUED"
    assert blog3.status == "QUEUED"

async def test_log_cleanup():
    """Test that logs are deleted after completion"""
    # Generate blog
    task_id = await generate_blog_with_logs()
    
    # Verify logs exist during generation
    logs = await log_manager.get_logs(task_id)
    assert len(logs) > 0
    
    # Wait for completion + cleanup delay
    await wait_for_completion(task_id)
    await asyncio.sleep(310)  # 5 min + buffer
    
    # Verify logs are deleted
    logs = await log_manager.get_logs(task_id)
    assert len(logs) == 0
```

#### Integration Tests

```python
# backend/src/tests/test_queue_integration.py

async def test_end_to_end_queue_flow():
    """Test complete queue flow from submission to completion"""
    # Submit blog
    response = await client.post("/queue-blog", json={
        "topic": "Test Topic",
        "instructions": "Test instructions"
    })
    task_id = response.json()["task_id"]
    
    # Verify queued
    blog = await get_blog(task_id)
    assert blog.status == "QUEUED"
    
    # Wait for processing to start
    await wait_for_status(task_id, "IN_PROGRESS")
    
    # Verify logs are available
    logs_response = await client.get(f"/generation-logs/{task_id}")
    assert logs_response.status_code == 200
    
    # Wait for completion
    await wait_for_status(task_id, "COMPLETED")
    
    # Verify logs are no longer available
    logs_response = await client.get(f"/generation-logs/{task_id}")
    assert logs_response.status_code == 404

async def test_retry_failed_blog():
    """Test regenerating a failed blog"""
    # Create failed blog
    task_id = await create_failed_blog()
    
    # Retry
    response = await client.post(f"/regenerate-blog/{task_id}")
    new_task_id = response.json()["task_id"]
    
    # Verify new blog is queued
    new_blog = await get_blog(new_task_id)
    assert new_blog.status == "QUEUED"
    assert new_blog.retryCount == 1
```

### Frontend Tests

```typescript
// src/tests/queue-system.test.tsx

describe('BlogQueueCard', () => {
  it('shows correct status badge for generating blog', () => {
    const blog: BlogData = {
      id: '1',
      status: 'IN_PROGRESS',
      progress: 45,
      // ...
    };
    
    render(<BlogQueueCard blog={blog} />);
    
    expect(screen.getByText('Generating (45%)')).toBeInTheDocument();
    expect(screen.getByText('View Logs')).toBeInTheDocument();
    expect(screen.getByText('View Draft')).toBeInTheDocument();
  });
  
  it('shows regenerate button for failed blogs', () => {
    const blog: BlogData = {
      id: '1',
      status: 'FAILED',
      retryCount: 0,
      maxRetries: 3,
      // ...
    };
    
    render(<BlogQueueCard blog={blog} />);
    
    expect(screen.getByText('Regenerate')).toBeInTheDocument();
  });
  
  it('disables regenerate after max retries', () => {
    const blog: BlogData = {
      id: '1',
      status: 'FAILED',
      retryCount: 3,
      maxRetries: 3,
      // ...
    };
    
    render(<BlogQueueCard blog={blog} />);
    
    const regenerateBtn = screen.queryByText('Regenerate');
    expect(regenerateBtn).toBeDisabled();
  });
});

describe('GenerationLogModal', () => {
  it('streams logs via SSE', async () => {
    // Mock SSE connection
    const mockEventSource = mockSSE();
    
    render(<GenerationLogModal blogId="1" isOpen={true} onClose={vi.fn()} />);
    
    // Emit log event
    mockEventSource.emit('message', {
      data: JSON.stringify({
        timestamp: '2025-01-19T10:30:00Z',
        step: 'research',
        message: 'Gathering information...'
      })
    });
    
    await waitFor(() => {
      expect(screen.getByText('Gathering information...')).toBeInTheDocument();
    });
  });
});
```

---

## Rollback Plan

### Rollback Triggers

1. **Critical bugs** in queue processing
2. **Data corruption** in blog records
3. **Performance degradation** (>50% slower than current system)
4. **User complaints** about confusing UX

### Rollback Steps

#### Step 1: Switch to Feature Flag (Immediate - 5 minutes)

```python
# backend/src/core/config.py
ENABLE_ASYNC_QUEUE = os.getenv("ENABLE_ASYNC_QUEUE", "false").lower() == "true"

# main.py
if ENABLE_ASYNC_QUEUE:
    # Use new queue system
    response = await queue_manager.enqueue_blog(...)
else:
    # Use old synchronous system
    response = await generate_blog_sync(...)
```

#### Step 2: Database Rollback (If needed - 15 minutes)

```bash
# Revert Prisma migration
cd frontend-nextjs/blog-generator-ui
npx prisma migrate resolve --rolled-back <migration_name>

# Restore from backup if needed
psql -U postgres -d bloggen < backup_before_queue_migration.sql
```

#### Step 3: Code Rollback (30 minutes)

```bash
# Revert to commit before async queue feature
git revert <commit-hash-range>

# Or checkout previous branch
git checkout main
git branch -D feature/async-queue

# Redeploy
make deploy
```

#### Step 4: Data Cleanup (1 hour)

```sql
-- Reset any blogs stuck in new states
UPDATE blogs
SET status = 'COMPLETED'
WHERE status IN ('QUEUED', 'IN_PROGRESS')
  AND updated_at < NOW() - INTERVAL '1 hour';

-- Clear queue-related fields
UPDATE blogs
SET queuePosition = NULL,
    retryCount = 0;
```

---

## Success Metrics

### Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Queue processing time | < 5 seconds | Time from QUEUED → IN_PROGRESS |
| Log retrieval speed | < 500ms | GET /generation-logs/:id response time |
| Draft fetch speed | < 300ms | GET /draft/:id response time |
| SSE connection time | < 2 seconds | Time to establish SSE stream |
| Memory usage | < 500MB | Redis memory for logs/drafts per blog |

### User Experience Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| User understands queue | > 90% | User survey: "I understand what 'Queued' means" |
| Finds log viewer useful | > 75% | Analytics: % users who click "View Logs" |
| Retry success rate | > 85% | Failed blogs that complete on retry |
| UI responsiveness | < 1 second | Time from click to UI update |

### System Health Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Queue overflow events | 0 | Blogs that fail to queue |
| Log cleanup success | > 99% | Logs deleted after completion |
| Draft cleanup success | > 99% | Drafts deleted after completion |
| Database query time | < 100ms | Queue lookup queries |

---

## Risk Analysis

### High-Risk Areas

1. **Queue deadlock**: Worker gets stuck, no jobs process
   - **Mitigation**: Watchdog timer, automatic worker restart
   - **Detection**: Monitor queue age, alert if blog queued > 10 minutes

2. **Memory leak**: Logs/drafts not cleaned up
   - **Mitigation**: Aggressive TTL on Redis keys
   - **Detection**: Redis memory monitoring, auto-cleanup job

3. **Race conditions**: Multiple workers start simultaneously
   - **Mitigation**: Distributed lock (Redis), single worker instance
   - **Detection**: Log worker starts, alert on duplicate workers

4. **Database corruption**: Migration fails mid-way
   - **Mitigation**: Transaction-based migration, backup before migration
   - **Detection**: Schema validation after migration

### Medium-Risk Areas

1. **SSE connection failures**: Logs don't stream
   - **Mitigation**: Fallback polling, reconnection logic
   - **Detection**: Connection state monitoring

2. **Draft not updating**: Sections missing
   - **Mitigation**: Section-level updates, idempotent operations
   - **Detection**: Draft update logs

3. **UI confusion**: Users don't understand queue
   - **Mitigation**: Clear status messages, onboarding tooltip
   - **Detection**: User surveys, support tickets

---

## Security Considerations

### Authentication & Authorization

1. **Log access control**
   - Users can only view logs for their own blogs
   - Logs are deleted after completion (no unauthorized access later)

2. **Draft access control**
   - Users can only view drafts for their own blogs
   - Drafts are deleted after completion

3. **Queue manipulation**
   - Users cannot modify queue position
   - Users cannot cancel other users' blogs

### Rate Limiting

```python
@rate_limit(max_requests=10, window=60)  # 10 blogs per minute
async def queue_blog(request: BlogGenerationRequest, user: User):
    # Prevent queue flooding
    pass
```

### Data Privacy

1. **Log retention**: Maximum 5 minutes after completion
2. **Draft retention**: Deleted immediately on completion
3. **Error messages**: No sensitive data in failure reasons

---

## Deployment Strategy

### Deployment Steps

1. **Pre-deployment**
   - Database backup
   - Feature flag OFF by default
   - Deploy code with queue disabled

2. **Staged rollout**
   - Day 1: Enable for ADMIN users only
   - Day 2: Enable for PREMIUM users
   - Day 3: Enable for FREE users
   - Day 4: Enable for all users

3. **Monitoring**
   - Watch error rates
   - Monitor queue processing times
   - Check Redis memory usage
   - Review user feedback

4. **Rollback readiness**
   - Keep old code branch ready
   - Database backup accessible
   - Feature flag can be toggled instantly

---

## Documentation Updates

### Files to Create/Update

1. **API Documentation**
   - `docs/ASYNC_QUEUE_API.md` - New endpoints
   - `docs/API_REFERENCE.md` - Update existing endpoints

2. **User Guide**
   - `docs/USER_GUIDE_ASYNC_QUEUE.md` - How to use queue system
   - Screenshots of new UI

3. **Developer Guide**
   - `docs/DEVELOPER_GUIDE_QUEUE.md` - Queue implementation details
   - Architecture diagrams

4. **Deployment Guide**
   - `docs/DEPLOYMENT_GUIDE.md` - Update with queue deployment steps

---

## Timeline Summary

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| Phase 1: Backend Queue Infrastructure | 3-4 days | Day 1 | Day 4 |
| Phase 2: Database Schema Updates | 1 day | Day 5 | Day 5 |
| Phase 3: Frontend Components | 3-4 days | Day 6 | Day 9 |
| Phase 4: API Client Updates | 1 day | Day 10 | Day 10 |
| Phase 5: Integration & Testing | 2-3 days | Day 11 | Day 13 |
| **Buffer** | 2 days | Day 14 | Day 15 |
| **Total** | **~15 days** | **Day 1** | **Day 15** |

---

## Approval Checklist

Before implementation begins, confirm:

- [ ] User requirements understood and validated
- [ ] Architecture design reviewed and approved
- [ ] Database schema changes reviewed
- [ ] API design reviewed and approved
- [ ] UI/UX mockups reviewed and approved
- [ ] Testing strategy agreed upon
- [ ] Rollback plan reviewed
- [ ] Timeline and resources allocated
- [ ] Security considerations addressed
- [ ] Documentation plan approved

---

## Next Steps

1. **User approval** of this design document
2. **Create detailed UI mockups** for new components
3. **Create task breakdown** in project management tool
4. **Set up feature branch**: `feature/async-queue-system`
5. **Begin Phase 1 implementation**

---

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Authors**: GitHub Copilot  
**Reviewers**: [To be added]
