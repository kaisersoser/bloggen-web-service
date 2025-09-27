# Frontend Optimization Requirements

_Last updated: 2025-09-27_

## Snapshot
- **Framework**: Next.js 15 (App Router, React 19)
- **Key entry points**: `src/app/blog/page.tsx`, `src/hooks/useBlogGenerator.ts`, `src/components/blog/TabbedPromptInterface.tsx`
- **Streaming architecture**: Custom `TimeoutResistantSSE` + enhanced console/draft preview flows

This report captures actionable opportunities to improve code quality, runtime performance, user experience, and roadmap-level features. Each item references concrete code locations to accelerate prioritization and implementation.

---

## 1. Codebase Structure & Maintainability

| Area | Issue / Observation | Recommendation | Impact |
|------|---------------------|----------------|--------|
| `useBlogGenerator.ts` (≈400 lines) | Monolithic hook coordinates auth, state orchestration, analytics, and SSE handling. Hard to reason about, duplicate logger noise. | Split into focused hooks: `useGenerationLifecycle` (state transitions), `useGenerationActions` (API orchestration), `useGenerationUiState`. Adopt `useReducer` for complex state. | High |
| `TabbedPromptInterface.tsx` (>500 lines) | Large component mixes console streaming, modal management, typewriter animation, and UI markup, making re-renders costly. | Break into child components (e.g., `PromptHeader`, `GenerationConsole`, `DraftPreviewModal`). Memoize with `React.memo` and move queue logic into a standalone hook/service. | High |
| Logger usage (`logger.info` etc.) | Hundreds of info-level logs in production-critical paths (`useEnhancedSSEConnection`, `useBlogGenerator`). Potential perf hit and noisy logs even at default warn level due to metadata building. | Gate verbose logs behind `logger.shouldLog('debug')`. Strip emoji prefixes in production builds. Provide build-time flag to remove debug logging. | Medium |
| State duplication (`jobs`, `taskLogs`, `previousBlogs`) | Manual arrays maintained in hooks; risk of stale data and race conditions (e.g., simultaneous SSE + fetch). | Leverage `@tanstack/react-query` (already installed) for blogs/stats/tasks. Cache invalidation becomes declarative; simplifies recovery logic. | High |
| Repeated token fetches | `useEnhancedSSEConnection` fetches `/api/auth/jwt-token` on every stream/open and acknowledgment, duplicating logic. | Centralize token acquisition in `lib/authToken.ts` with memoization and expiry tracking. Optionally use NextAuth `getToken()` server action to embed token in SSE URL generation. | Medium |
| Message queue utilities | Queue management lives inside UI components with refs and manual timers. | Extract to utility (or Web Worker) that emits batched updates to reduce component complexity. | Medium |

---

## 2. Performance Optimizations

1. **Console message growth** (`useConsoleMessages`):
   - Messages append indefinitely; long-running sessions may trigger memory leaks and DOM bloat.
   - **Actions**: Impose cap (e.g., 300 entries) and archive overflow separately; consider virtualization via `react-window` (already dependency).

2. **Typewriter effect latency** (`TabbedPromptInterface`):
   - Per-message `setTimeout` (800–3000 ms) blocks new logs when backlog large.
   - **Actions**: Use `requestIdleCallback`/`scheduler.postTask` to process queue during idle time. Offer toggle to disable animation for power users.

3. **Streaming reconnection** (`TimeoutResistantSSE`):
   - On errors, entire payload reprocessed, and content buffer can grow large. No max retries for completed tasks.
   - **Actions**: Auto-clean `contentBuffer` per task completion/error; de-dupe progress events. Consider server-sent `retry` header to offload logic.

4. **Bundle weight**:
   - Icons and dialog components imported at top-level. On blog page load, Draft Preview modal loads even when closed.
   - **Actions**: Dynamic import heavy subcomponents (`StreamingConsole`, `DraftPreviewModal`), lazy-load icon sets (use `dynamic(() => import('lucide-react/...'))`).

5. **Network efficiency**:
   - `blogService.getUserBlogs()` fetches entire list even for small UI previews; triggered multiple times (`useBlogGenerator`, `useBlogManagement`).
   - **Actions**: Introduce pagination or delta updates; use SSE events to push completion updates directly, avoiding refetch.

6. **Logging overhead**:
   - Logger constructs large context objects even when dropped by level filter.
   - **Actions**: Wrap metadata creation inside `if (logger.shouldLog('debug')) { … }` to avoid string slicing and heavy arrays when log not emitted.

---

## 3. User Experience Enhancements

| Experience Gap | Suggested Improvement | Notes |
|----------------|-----------------------|-------|
| Console readability | Add filters (errors only, agent steps, tooling). Provide search and copy-to-clipboard per entry. | Build on existing message types (`status`, `agentthinking`). |
| Draft preview | Allow inline editing + “promote edits to final output” flow. Persist partial drafts to local storage to survive refreshes. | Use `useStreamingContent` to sync edits. |
| Generation workflow | Provide skeleton loaders for `BlogTileGrid` and progress indicators (percentage + phases). | Use `next/font` & `framer-motion` micro-interactions. |
| Error recovery | Centralize human-friendly messages (network, auth, SSE) and show inline callouts with one-click retry. | Create `useErrorToast` hook; integrate with ShadCN toast. |
| Accessibility | Ensure console is screen-reader friendly (ARIA live regions). Provide keyboard shortcuts? | Break long emoji strings into descriptive text. |
| Mobile layout | Validate responsive behavior of tabbed interface and modals; consider bottom sheet for console on mobile. | Use CSS container queries. |

---

## 4. Functional & Feature Opportunities

1. **Generation history insights**: Add analytics view (top topics, success rate) using existing Prisma data and `recharts` dependency.
2. **Template system**: Allow saved prompt templates per role. Use Zustand or React Context to manage template library.
3. **Collaborative review**: Integrate comment threads or shareable links for generated drafts.
4. **Retry / resume**: Provide “duplicate task” button that reuses instructions but tweaks parameters (e.g., tone, length) before re-run.
5. **Quality guardrails**: Inline fact-check prompts or Grammarly-style checks once SSE finalizes content.
6. **Notifications**: Hook into enhanced notification plan—deliver toast/web push when generation completes in background.

---

## 5. Tooling, Testing, and Observability

- **Testing coverage**: Add focused component tests (React Testing Library) for `TabbedPromptInterface` logic (queue flush, tab switching) and hooks (`useEnhancedSSEConnection` mocking EventSource).
- **Performance budgets**: Adopt Next.js `instrumentation.ts` to log TTFB/INP. Monitor SSE latency and queue size.
- **CI lint rules**: Configure ESLint “complexity” and `no-console` (production builds) to enforce structure improvements.
- **Developer ergonomics**: Provide Storybook stories for core components (console, prompt tabs) to iterate on UX quickly.
- **Telemetry**: Emit structured events (start, progress, completion) to analytics provider to understand drop-offs.

---

## 6. Prioritization Matrix

| Priority | Recommendation |
|----------|----------------|
| **P0** (Immediate value) | Refactor `useBlogGenerator` into composable hooks; cap console message growth; throttle verbose logging. |
| **P1** (Next sprint) | Modularize `TabbedPromptInterface`; migrate blog/stats fetching to React Query; streamline token management. |
| **P2** (Roadmap) | Dynamic loading of heavy components; user-facing console filters; background notifications. |
| **P3** (Strategic) | Collaborative review features; full analytics dashboard. |

---

## 7. Unused Code Assessment

Latest scan (`2025-09-27`):

```bash
cd frontend-nextjs/blog-generator-ui
npx --yes ts-prune
```

High-signal findings (manual triage required before removal):

| Category | Candidate | Notes |
|----------|-----------|-------|
| Legacy hooks | `src/hooks/useEnhancedSSEConnection.ts`, ~~`src/hooks/useSSEConnection.ts`~~ (removed), `src/hooks/useStreamingBlogGeneration.ts` | `useEnhancedSSEConnection` now primary; confirm if `useStreamingBlogGeneration` still needed. |
| Alternative SSE impls | ~~`src/hooks/useOptimizedSSE.ts`~~ (removed), ~~`src/hooks/useWebSocketConnection.ts`~~ (removed) | Legacy experimentation retired during Priority 1 cleanup. |
| Blog UI variants | `AgenticChatInterface`, `BlogGenerationView`, `BlogHistorySidebar`, `MinimizedCrewConsole` | Not mounted in production routes. Either archive under `legacy/` or remove after design sign-off. |
| Skeletons | `BlogHistorySkeleton`, `BlogGenerationSkeleton`, `ConsoleSkeleton` | Unused after recent redesign; keep if upcoming skeleton states require them. |
| Services | `src/lib/supabase.ts` exports (`supabase`, `supabaseAdmin`, `isUsingSupabase`) | No active references post-Prisma migration. Double-check server utilities before deletion. |
| Types | `AnalyticsResponse`, `ContentStreamMessage`, `ProgressStreamMessage` | Reserved for analytics roadmap; move to `types/legacy` if deferred long-term. |

False positives (safe to ignore): Next.js-required defaults (`next.config.ts`, `src/app/page.tsx`, route handler exports) and internal helper exports flagged by `ts-prune` as “used in module”.

**Cleanup pathway**
1. Apply repo cleanup rulebook: exhaustive import search, config check, and staged validation per file.
2. Group confirmed-legacy assets under `src/legacy/` before deletion to simplify rollbacks.
3. Enable `noUnusedLocals` / `noUnusedParameters` in `tsconfig.json` once refactor lands to prevent regressions.
4. Add `ts-prune` (report-only) to CI to surface new unused exports.

---

### Next Steps
1. Review P0 items with engineering leads; estimate refactor effort and testing scope.
2. Create technical design docs for SSE refactor and React Query adoption.
3. Schedule UX audit to validate console and mobile experience improvements.
4. Set up metrics collection before/after optimizations to track wins.

> _This document is intended as a living artifact—update after major refactors or new feature launches._
