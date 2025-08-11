# CrewAI Blog Generation Service - AI Agent Instructions

## 🚨 CRITICAL DEVELOPMENT RULES 🚨

### ⚠️ Rule #1: Virtual Environment Requirement
**ALWAYS activate the virtual environment before running Python scripts in Agent mode**
- Backend Python environment: `source backend/.venv/bin/activate` (Linux/Mac) or `backend\.venv\Scripts\activate` (Windows)
- Running Python scripts without the virtual environment WILL FAIL
- This includes testing, debugging, and any Python script execution
- Example: `cd backend && source .venv/bin/activate && python src/main.py`

### ⚠️ Rule #2: Major Changes Approval Process
**DO NOT make major changes without comprehensive planning and approval**
- **Major changes** include: New features, architectural changes, database schema changes, API modifications, authentication changes
- **Process**: 
  1. Provide a detailed plan with scope, impact analysis, and implementation steps
  2. Wait for explicit approval before proceeding
  3. Break down large changes into smaller, reviewable chunks
- **Minor changes** (bug fixes, small improvements, configuration tweaks) can proceed without approval
- When in doubt, ask for clarification before implementing

## Code Quality Principles

### Principles of Writing Good Code

#### 1. Clarity Over Cleverness
- Prioritize readability and understanding over clever tricks.
- Code should be easy to follow by other developers (or your future self).

#### 2. Keep It Simple (KISS)
- Solve problems using the simplest possible solution.
- Avoid over-engineering and unnecessary abstraction.

#### 3. Don't Repeat Yourself (DRY)
- Reuse code through functions, classes, or modules.
- Eliminate duplicate logic to reduce maintenance overhead.

#### 4. Single Responsibility Principle
- Each function, class, or module should have one clear purpose.
- Improves modularity and testability.

#### 5. Write Self-Documenting Code
- Use descriptive names for variables, functions, and classes.
- Structure code to make its intent obvious without needing excessive comments.

#### 6. Test Thoroughly
- Write unit and integration tests for critical code paths.
- Use tests to verify correctness and catch regressions early.

#### 7. Refactor Often
- Regularly revisit and improve existing code.
- Clean up code as you go to prevent technical debt.

#### 8. Follow Consistent Style
- Use a consistent code style and follow language conventions.
- Prefer automated tools (linters, formatters) to enforce style.

#### 9. Use the Right Tools and Patterns
- Apply appropriate design patterns where they improve structure and clarity.
- Leverage modern development tools and best practices.

#### 10. Code with Collaboration in Mind
- Write code as if someone else will read and modify it.
- Leave helpful comments where logic is complex or non-obvious.

## Architecture Overview

This is a **full-stack AI blog generation service** using CrewAI Flows, Next.js with authentication, and real-time streaming. The system orchestrates multiple AI agents (researcher, content creator, fact checker, finalizer) to collaboratively generate high-quality blogs with automatic image integration.

### Core Components
- **Backend**: Python Flask + CrewAI Flows + SSE streaming (`backend/src/`)
- **Frontend**: Next.js 14 + NextAuth.js + TypeScript (`frontend-nextjs/blog-generator-ui/`)
- **Database**: PostgreSQL + Prisma ORM (user management) + ChromaDB (vector storage)
- **Authentication**: Role-based JWT system (FREE/PREMIUM/ADMIN with generation limits)
- **External APIs**: OpenAI (content generation) + Unsplash (image integration)

## Critical Development Patterns

### CrewAI Flow Architecture
- **Flow-based orchestration**: Use `BlogGenerationFlow` class in `backend/src/bloggen/flows.py`
- **4-phase workflow**: Research → Content Generation → Fact Checking → Finalization
- **Agent definition**: Agents are defined **programmatically** within the Flow class methods, not YAML
- **Status callbacks**: Each flow phase calls `status_callback` for real-time SSE updates

```python
# Agent creation pattern within Flow methods
researcher = Agent(
    role='Senior Researcher',
    goal='Uncover cutting-edge developments and insights in the given topic',
    verbose=True,
    backstory="""You work at a leading tech think tank...""",
    tools=self._get_research_tools(),
    allow_delegation=False
)

# Status update pattern for CrewAI flows
def _send_status_update(self, step_name, progress, details):
    if self.status_callback:
        self.status_callback(step_name, progress, details)
```

### Real-Time Communication
- **SSE streaming**: `/stream/<task_id>` endpoint for real-time progress updates
- **JWT authentication**: SSE uses query parameter authentication (EventSource limitation)
- **Frontend SSE handling**: `connectToTaskStream()` in `page.tsx` manages EventSource connections
- **Task state management**: Jobs stored in React state with progress tracking

### Authentication & Authorization
- **NextAuth.js setup**: Multi-provider OAuth (Google, GitHub) with JWT strategy
- **Role-based access**: Middleware decorators `@require_auth`, `@require_role`, `@check_generation_limits`
- **Generation limits**: FREE (3/month), PREMIUM (50/month), ADMIN (unlimited)
- **Database integration**: Prisma schema tracks users, sessions, blog generation history

### Image Integration
- **Automatic image search**: `UnsplashImageTool` in `backend/src/bloggen/tools/unsplash_tool.py`
- **Markdown generation**: Tool outputs formatted `![alt](url "caption")` syntax
- **Fallback placeholders**: When Unsplash API unavailable, generates placeholder images

## Essential Development Commands

### Setup & Development
```bash
# Full stack development
make install && make dev

# Backend only (Flask + CrewAI)
cd backend && python src/main.py

# Frontend only (Next.js)
cd frontend-nextjs/blog-generator-ui && npm run dev

# Database setup
cd frontend-nextjs/blog-generator-ui && npx prisma db push
```

### Docker Deployment
```bash
# Full production deployment
docker-compose up -d

# HTTPS is enforced in ALL environments - use local certificates for development
```

## Key Configuration Points

### Environment Variables
- **Backend**: `OPENAI_API_KEY`, `UNSPLASH_ACCESS_KEY`, `NEXTAUTH_SECRET`
- **Frontend**: `NEXTAUTH_URL`, `DATABASE_URL`, `GOOGLE_CLIENT_ID`, `GITHUB_ID`
- **HTTPS enforcement**: Configured in `backend/src/https_config.py`

### API Endpoint Patterns
- **Protected routes**: All blog generation endpoints require authentication
- **User isolation**: Users can only access their own blogs/tasks (except ADMIN role)
- **Rate limiting**: Generation limits enforced per user role in middleware

### Modular Frontend Architecture
- **Page components**: Keep pages lightweight, delegate logic to hooks and services
- **Custom hooks**: Extract stateful logic (`useAuth`, `useUserStats`, `useSSEConnection`)
- **Service layer**: API interactions centralized in `src/lib/services/`
- **Component composition**: Break complex UI into smaller, reusable components
- **Type definitions**: Shared interfaces in `src/types/` for consistent data contracts

```typescript
// Example modular structure
// src/hooks/useSSEConnection.ts - SSE logic
// src/components/blog/BlogCard.tsx - Reusable card
// src/components/blog/BlogModal.tsx - Modal component  
// src/lib/services/blog.ts - API calls
// src/types/blog.ts - Type definitions
```

### File Structure Conventions
- **Flow definitions**: Main logic in `backend/src/bloggen/flows.py` with programmatic agent creation
- **Legacy crew setup**: YAML-based configs exist in `backend/src/bloggen/config/` but are NOT used by main app
- **Custom tools**: Python classes in `backend/src/bloggen/tools/`
- **Frontend components**: React/TypeScript in `src/components/` with shadcn/ui
- **Custom hooks**: Business logic in `src/hooks/` (e.g., `useAuth.ts`, `useUserStats.ts`)
- **Service layer**: API interactions in `src/lib/services/` (e.g., `user.ts`)
- **Database models**: Prisma schema in `frontend-nextjs/blog-generator-ui/prisma/schema.prisma`

### React/Next.js Best Practices
- **Component reusability**: Extract reusable UI components (e.g., `BlogCard`, `JobCard`) to avoid duplication
- **Custom hooks**: Use hooks for stateful logic like authentication (`useAuth`), user stats (`useUserStats`)
- **Service abstraction**: Keep API calls in service layer (`src/lib/services/`) separate from components
- **Type safety**: Use TypeScript interfaces for consistent data shapes (`JobState`, `BlogData`, `ErrorInfo`)
- **Modular architecture**: Split large page components into smaller, focused components

```typescript
// Example: Extract reusable BlogCard component
const BlogCard = ({ blog, onClick, variant = "default" }) => (
  <div onClick={() => onClick(blog)} className="cursor-pointer hover:scale-105">
    {/* Reusable card content */}
  </div>
)

// Use across different views
{previousBlogs.map(blog => (
  <BlogCard key={blog.id} blog={blog} onClick={openBlogDetails} />
))}
```

## Integration Points

### CrewAI ↔ Flask Integration
- **Flow instantiation**: Create flows with `status_callback` parameter for SSE streaming
- **Background execution**: Use threading to run flows asynchronously while serving HTTP
- **Task persistence**: Store task status in global dictionaries for SSE endpoint access

### Frontend ↔ Backend Communication
- **JWT token flow**: Frontend gets token from `/api/auth/jwt-token`, includes in API headers
- **SSE connection**: Frontend connects to `/stream/<task_id>?token=<jwt>` for real-time updates
- **Error handling**: Structured error responses with user-friendly messages
- **Service abstraction**: All API calls encapsulated in service classes for testability and reuse

### Component Architecture Patterns
- **Container vs Presentational**: Separate data-fetching logic from UI rendering
- **Custom hooks for state**: Extract complex state logic into reusable hooks
- **Event handlers as props**: Pass event handlers down rather than inline functions
- **Consistent loading states**: Use standardized loading and error components

### External API Integrations
- **OpenAI**: Configured via CrewAI agents, uses `OPENAI_API_KEY`
- **Unsplash**: Custom tool class, handles rate limiting and fallbacks
- **Database**: Prisma ORM handles user management, ChromaDB for vector storage

## Security Considerations

- **HTTPS enforcement**: All environments require HTTPS (see `HTTPS_SECURITY.md`)
- **JWT validation**: Custom middleware validates NextAuth.js tokens
- **CORS configuration**: Dynamic origins based on environment
- **Input validation**: Request body validation for all endpoints
- **Role-based access**: Strict permission checks on all protected resources

## Testing & Debugging

- **CrewAI verbose mode**: Set `verbose: true` in agent configs for detailed logging
- **SSE debugging**: Check browser Network tab for EventSource connections
- **Database inspection**: Use Prisma Studio or direct PostgreSQL queries
- **Log locations**: CrewAI logs in `backend/src/bloggen/logs/`
