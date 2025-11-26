# CrewAI Blog Generation Service - AI Agent Instructions

## 🚨 CRITICAL DEVELOPMENT RULES 🚨

### ⚠️ Rule #0: Git Branch Strategy (HIGHEST PRIORITY)
**ALWAYS work in the correct branch following the established git workflow**

#### Complete Workflow
```
prototype-agent-flow (EXPERIMENTAL - testing new ideas)
    ↓
development (DEVELOPMENT - main development environment)
    ↓
feature/staging-environment (STAGING - production testing)
    ↓
main (PRODUCTION - auto-deploys to Railway + Vercel)
```

#### CRITICAL: THIS IS THE STAGING ENVIRONMENT
**THIS VSCODE WORKSPACE IS FOR STAGING-TO-PRODUCTION WORKFLOW ONLY**

#### Allowed Operations in This Environment
1. **Primary Work Location**: `feature/staging-environment` branch
   - Test production-ready features
   - Final validation before production deployment
   - Bug fixes and refinements for production
   - User tests on Windows Docker staging environment (docker-compose.staging.yml)

2. **Production Deployment**: Merge `feature/staging-environment` → `main` ONLY
   - Only merge when ALL staging tests pass completely
   - Triggers automatic deployment to Railway (backend) + Vercel (frontend)
   - User explicitly requests production deployment
   - Example: `git checkout main && git merge feature/staging-environment --no-ff`

#### FORBIDDEN Operations in This Environment
- ❌ **NEVER make changes to `development` branch from this environment**
- ❌ **NEVER merge anything into `development` branch**
- ❌ **NEVER checkout `development` branch for editing**
- ❌ **NEVER work in `prototype-agent-flow` branch**
- ❌ This environment is STAGING → PRODUCTION only
- ❌ Development work happens in a separate development environment

#### Critical Rules - READ CAREFULLY
- ✅ **DO**: ALWAYS work in `feature/staging-environment` branch
- ✅ **DO**: Switch to `feature/staging-environment` at the start of every session
- ✅ **DO**: Merge to `main` ONLY when user requests production deployment
- ✅ **DO**: Always ask user before merging to `main`
- ✅ **DO**: Reject any requests to modify `development` or `prototype-agent-flow` branches
- ❌ **DON'T**: NEVER make changes directly in `main` branch
- ❌ **DON'T**: NEVER work in `main` branch - it's production only
- ❌ **DON'T**: NEVER modify `development` branch - use development environment for that
- ❌ **DON'T**: Push to `main` without explicit user approval

#### Branch Access Control
- **Active Branch**: `feature/staging-environment` (STAGING)
- **When session starts**: ALWAYS run `git checkout feature/staging-environment`
- **If in wrong branch**: Switch immediately to `feature/staging-environment`
- **If user requests development work**: Inform them this is the staging environment and reject the request
- **Check current branch**: `git branch --show-current`

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

### ⚠️ Rule #3: Test File Organization
**ALWAYS place test files in the proper directory structure**
- **Backend test files**: Must be placed in `backend/src/tests/` directory
- **Frontend test files**: Must be placed in `frontend-nextjs/blog-generator-ui/src/tests/` directory
- **NO test files** should be created in root directories or other locations
- Examples: 
  - Create `backend/src/tests/test_my_feature.py` NOT `backend/test_my_feature.py`
  - Create `frontend-nextjs/blog-generator-ui/src/tests/test-component.html` NOT `frontend-nextjs/blog-generator-ui/test-component.html`

### ⚠️ Rule #4: Documentation File Organization
**ALWAYS place documentation files in the proper directory structure**
- **Backend documentation**: Must be placed in `backend/docs/` directory
- **Frontend documentation**: Must be placed in `frontend-nextjs/blog-generator-ui/docs/` directory
  - Use subdirectories: `architecture/`, `features/`, `guides/`, `archive/`
- **Project-wide documentation**: Goes in root-level `docs/` directory
- **NO documentation files** should be created in root directories unless project-wide
- Examples:
  - Create `backend/docs/API_GUIDE.md` NOT `backend/API_GUIDE.md`
  - Create `frontend-nextjs/blog-generator-ui/docs/features/COMPONENT_GUIDE.md` NOT `frontend-nextjs/blog-generator-ui/COMPONENT_GUIDE.md`

### ⚠️ Rule #5: HTTPS-Only Development
**ALWAYS run the frontend in HTTPS mode**
- **Frontend development**: Always use `npm run dev` (which now defaults to HTTPS via `dev-https.js`)
- **HTTP fallback**: Only use `npm run dev:http` for specific debugging scenarios
- **HTTPS is enforced** in ALL environments including development
- **SSL certificates**: Located in `frontend-nextjs/blog-generator-ui/certs/` directory
- This ensures consistent behavior between development and production environments

### ⚠️ Rule #6: Code Cleanup Best Practices
**MANDATORY PROCESS for any code cleanup tasks - NO EXCEPTIONS**

#### Pre-Cleanup Analysis (REQUIRED)
1. **Complete Dependency Mapping**:
   - Search for ALL imports of each file across the entire codebase using `grep -r "filename" src/`
   - Check for dynamic imports, lazy loading, or conditional usage
   - Verify no indirect dependencies through re-exports or barrel files
   - Search in configuration files, tests, documentation, and JSON files

2. **Reference Validation**:
   - Use `find . -name "*.ts*" -exec grep -l "filename" {} \;` to find all references
   - Check for usage in package.json, config files, and build scripts
   - Verify no runtime dependencies or reflection-based usage
   - Search for string references that might indicate dynamic imports

3. **Compilation Verification**:
   - Run `npm run build` before making ANY changes to establish baseline
   - Comment out exports first to see what breaks during compilation
   - Never delete files without first confirming zero references

#### Cleanup Process (MANDATORY STEPS)
1. **Create Analysis Report FIRST**:
   - List all files proposed for deletion with full dependency analysis
   - Show complete reference search results for each file
   - Get explicit approval before proceeding with ANY deletions
   
2. **Gradual Removal Process**:
   - Remove ONE file at a time only
   - Run full compilation after EACH deletion: `npm run build`
   - Fix any broken imports immediately before proceeding
   - Maintain detailed rollback plan for each deletion

3. **Validation Requirements**:
   - Verify functionality works end-to-end after cleanup
   - Check for broken imports, type errors, and runtime issues
   - Test that all existing features continue to work
   - Document what was removed and why in a cleanup report

#### Forbidden Actions
- **NEVER delete files without comprehensive reference analysis**
- **NEVER assume files are unused based on limited searches**
- **NEVER delete multiple files simultaneously**
- **NEVER proceed without explicit approval for file deletions**

#### Failure Recovery
- If ANY compilation errors occur, immediately restore deleted files
- If functionality breaks, rollback ALL changes and reassess
- Always have a clear restoration path before making changes

### ⚠️ Rule #7: AI Image Generation Cost Management
**CRITICAL: AI image generation is DISABLED by default for cost savings**

#### Image Generation Toggle System
- **Current State**: AI image generation is **DISABLED** (cost optimization)
- **Location**: Settings stored in `backend/.env` file
- **Toggle Script**: Use `backend/toggle_image_generation.py` for easy enable/disable

#### Configuration Settings
Three granular toggles control different aspects of image generation:
```bash
ENABLE_AI_IMAGE_GENERATION=false      # Master toggle for OpenAI DALL-E usage
ENABLE_HERO_IMAGE_GENERATION=false    # Hero images in main.py
ENABLE_CONTENT_IMAGE_INJECTION=false  # Automatic image injection in blog content
```

#### Quick Toggle Commands
```bash
# Disable AI image generation (SAVE COSTS - Current default)
cd backend && source .venv/bin/activate
python src/utils/toggle_image_generation.py disable

# Enable AI image generation (INCREASES COSTS)
cd backend && source .venv/bin/activate  
python src/utils/toggle_image_generation.py enable

# After any toggle, restart backend:
python src/main.py
```

#### Cost Impact
- **When DISABLED** (current): ❌ No OpenAI DALL-E API calls, ✅ Only free Unsplash images
- **When ENABLED**: 💸 OpenAI image generation costs ~$0.040 per image (DALL-E 3)
- **Typical blog**: 1 hero + 2-3 content images = ~$0.12-0.16 per blog in image costs

#### Implementation Details
- **Hero Image Generation**: `backend/src/main.py` conditionally calls OpenAIImageTool
- **Content Tools**: `backend/src/bloggen/tools_manager.py` conditionally loads OpenAIImageTool  
- **Content Injection**: `backend/src/bloggen/flows.py` conditionally runs mandatory image injection
- **Configuration**: `backend/src/core/config.py` FeatureConfig dataclass with environment variable loading

#### When to Re-enable
- For production deployments requiring premium visuals
- When cost budget allows for enhanced image quality
- For specific client requirements demanding AI-generated images
- Always verify current toggle state before debugging image-related issues

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

# Frontend only (Next.js HTTPS)
cd frontend-nextjs/blog-generator-ui && npm run dev

# Frontend HTTP fallback (debugging only)
cd frontend-nextjs/blog-generator-ui && npm run dev:http

# Database setup
cd frontend-nextjs/blog-generator-ui && npx prisma db push
```

### Image Generation Management
```bash
# Disable AI image generation (save costs - current default)
cd backend && source .venv/bin/activate && python toggle_image_generation.py disable

# Enable AI image generation (increases costs)
cd backend && source .venv/bin/activate && python toggle_image_generation.py enable

# Check current configuration
cd backend && grep -E "ENABLE_.*IMAGE" .env
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
- **Custom hooks**: Extract stateful logic (`useAuth`, `useUserStats`, `useGenerationLifecycle`, `useEnhancedSSEConnection`)
- **Service layer**: API interactions centralized in `src/lib/services/`
- **Component composition**: Break complex UI into smaller, reusable components
- **Type definitions**: Shared interfaces in `src/types/` for consistent data contracts

```typescript
// Example modular structure
// src/hooks/useGenerationLifecycle.ts - Orchestrates generation lifecycle
// src/hooks/useEnhancedSSEConnection.ts - SSE connection management
// src/components/blog/BlogCard.tsx - Reusable card
// src/components/blog/BlogModal.tsx - Modal component  
// src/lib/services/blog.ts - API calls
// src/types/blog.ts - Type definitions
```

### File Structure Conventions
- **Flow definitions**: Main logic in `backend/src/bloggen/flows.py` with programmatic agent creation
- **Legacy crew setup**: YAML-based configs exist in `backend/src/bloggen/config/` but are NOT used by main app
- **Custom tools**: Python classes in `backend/src/bloggen/tools/`
- **Backend tests**: All test files in `backend/src/tests/` directory
- **Backend documentation**: All docs in `backend/docs/` directory  
- **Backend utilities**: Utility scripts in `backend/src/utils/` directory
- **Frontend components**: React/TypeScript in `src/components/` with shadcn/ui
- **Frontend tests**: All test files in `frontend-nextjs/blog-generator-ui/src/tests/` directory
- **Frontend documentation**: All docs in `frontend-nextjs/blog-generator-ui/docs/` directory
  - Organized into subdirectories: `architecture/`, `features/`, `guides/`, `archive/`
- **Frontend utilities**: Utility scripts in `frontend-nextjs/blog-generator-ui/src/utils/` directory
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

## Project Directory Structure

### 📁 **Organized Project Layout**
```
bloggen-web-service/
├── backend/
│   ├── docs/                      # 📚 Backend documentation
│   ├── src/
│   │   ├── tests/                 # 🧪 Backend test files
│   │   ├── utils/                 # 🛠️ Backend utility scripts
│   │   ├── bloggen/               # Core blog generation logic
│   │   ├── config/                # Configuration modules
│   │   ├── core/                  # Core system modules
│   │   ├── api.py
│   │   └── main.py
│   └── [other backend files...]
├── frontend-nextjs/blog-generator-ui/
│   ├── src/
│   │   ├── docs/                  # 📚 Frontend documentation
│   │   ├── tests/                 # 🧪 Frontend test files
├── frontend-nextjs/blog-generator-ui/
│   ├── src/
│   │   ├── docs/                  # ❌ DEPRECATED - use docs/ instead
│   │   ├── tests/                 # 🧪 Frontend test files
│   │   ├── utils/                 # 🛠️ Frontend utility scripts
│   │   ├── app/                   # Next.js application routes
│   │   ├── components/            # React components
│   │   ├── hooks/                 # Custom React hooks
│   │   ├── lib/                   # Library code and services
│   │   └── [other frontend directories...]
│   ├── docs/                      # 📚 Frontend documentation (NEW location)
│   │   ├── architecture/          # Design and structure docs
│   │   ├── features/              # Feature-specific docs
│   │   ├── guides/                # Setup and debugging guides
│   │   └── archive/               # Historical reports
│   └── [other frontend files...]
├── docs/                          # 📚 Project-wide documentation
├── database/                      # 🗄️ Database scripts and backups
└── [project root files...]
```

### 🎯 **Key Organization Rules**
1. **Backend tests** → `backend/src/tests/`
2. **Backend docs** → `backend/docs/`
3. **Backend utils** → `backend/src/utils/`
4. **Frontend tests** → `frontend-nextjs/blog-generator-ui/src/tests/`
5. **Frontend docs** → `frontend-nextjs/blog-generator-ui/docs/` ⚠️ CHANGED from src/docs/
6. **Frontend utils** → `frontend-nextjs/blog-generator-ui/src/utils/`
7. **Project-wide docs** → `docs/`

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
