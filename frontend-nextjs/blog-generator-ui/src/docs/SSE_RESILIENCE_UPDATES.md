# SSE Resilience Updates (Priority 2)

_Last updated: 2025-09-27_

## Overview

Priority 2 focused on hardening the frontend streaming layer so long-running blog generations remain observable even when the browser, network, or token state is unstable. The work landed in three areas:

1. **Adaptive transport** – a rebuilt `TimeoutResistantSSE` client now refreshes stream URLs on demand, applies exponential backoff with jitter, and pauses retries while the browser is offline.
2. **State propagation** – `useEnhancedSSE` emits typed connection lifecycle events which `useGenerationLifecycle` records directly on each `JobState`.
3. **User feedback** – the Console tab surfaces connection status badges so users see what the system is doing during reconnects or outages.

## Key Code Changes

| Area | File(s) | Notes |
| --- | --- | --- |
| SSE client | `src/lib/TimeoutResistantSSE.ts` | URL factory support, adaptive backoff, offline awareness, chunk aggregation. |
| Hook integration | `src/hooks/useEnhancedSSE.ts`, `src/hooks/useGenerationLifecycle.ts` | New `ConnectionStateChange` callback keeps job records in sync with connection telemetry. |
| Job model | `src/types/blog.ts`, `src/hooks/useBlogManagement.ts` | Added `connectionState`, `connectionMessage`, and `connectionUpdatedAt` fields. |
| UI | `src/components/blog/TabbedPromptInterface.tsx`, `src/components/ui/SSEConnectionStatus.tsx` | Console tab shows live status banner (connecting, reconnecting, offline wait, closed, error). |

## Connection Lifecycle Cheat Sheet

The enhanced hook now emits the following status values. They map 1:1 to `JobState.connectionState` and the UI badge styling.

| Status | Trigger | Typical Message |
| --- | --- | --- |
| `connecting` | Initial `connect()` call | "Connecting to live updates…" |
| `connected` | Stream established or recovered | "Connection restored (attempt N)" |
| `reconnecting` | Retry scheduled after failure | "Reconnecting in X.X seconds…" |
| `offline_wait` | Browser reports `navigator.onLine === false` | "Offline detected. Waiting for network before retrying…" |
| `closed` | Manual close, completion, or backend termination | "Live updates completed" / reason string |
| `error` | Exhausted retries or fatal startup failure | Surfaced error message |

## Integration Guidance

- **When starting a new consumer** use `connectToTaskStream(..., onLogUpdate, onConnectionStateChange)` and persist the state if you need UI feedback.
- **Persisting status** – call `updateJob(taskId, { connectionState, connectionMessage, connectionUpdatedAt })` to keep shared stores aligned.
- **UI reuse** – import `SSEConnectionStatus` and hand it the job fields. Optional `onRetry` can wire back to your recovery logic if you want manual retries.
- **Manual closes** – ensure you clear cached connection state when shutting down streams (`closeActiveConnection` now does this automatically).

## Testing & Observability

- `npm run lint` covers TypeScript soundness for the new fields and hook signatures.
- To exercise reconnection logic locally, kill the backend or toggle the browser offline – the console badge should flip through `offline_wait → reconnecting → connected` once the service is back.
- Server-sent `error` events still flow through the console logs while connection-level failures are highlighted via the badge.

## Follow-Up Ideas

- Capture connection telemetry in a dedicated store for cross-page visibility.
- Add Playwright coverage that simulates offline/online transitions to guard the new UI signals.
- Explore toast notifications for persistent failures when the console tab is not focused.
