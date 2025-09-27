# Verbose Frontend Logging Toggle

This guide explains how to control the new verbose logging guard that protects high-volume client and server logs in the blog generator UI.

## Overview

- The flag `NEXT_PUBLIC_ENABLE_VERBOSE_LOGGING` controls whether chatty `logger.info` statements execute in production-like environments.
- By default, verbose logging is **disabled** in all production builds to avoid unnecessary console noise and the performance overhead that previously impacted SSE streaming.
- Local development (`NODE_ENV !== 'production'`) still receives full logs automatically; you only need the flag when you want to surface them in staging or production.

## Base log-level controls

Two additional environment variables determine the minimum severity that the loggers will emit:

- `LOG_LEVEL` sets the threshold for backend/Edge logging performed through `serverLogger`. Typical values are `warn`, `info`, or `debug`.
- `NEXT_PUBLIC_LOG_LEVEL` defines the same threshold for the browser-side logger.

Keep both values aligned to avoid drifting behaviour between server and client. For day-to-day operations use `warn`; escalate to `info` or `debug` only long enough to gather the required evidence, then revert.

> **Tip:** The verbose toggle and the base log levels work together. When `NEXT_PUBLIC_ENABLE_VERBOSE_LOGGING=true`, the guard allows chatty messages through, but they still respect the level threshold. If the level remains at `warn`, the info-level chatter will still be filtered out.

## When to Enable

Turn the flag on only for targeted investigations, such as:

- Reproducing streaming issues that require detailed SSE trace output.
- Debugging blog lifecycle hooks where timing information matters.
- Auditing protocol configuration differences between environments.

Disable it immediately after the investigation to restore standard logging levels.

## How to Use

1. Open the environment file that matches your deployment target:
   - Local overrides: `frontend-nextjs/blog-generator-ui/.env.local`
   - Shared defaults or CI/CD secrets: `frontend-nextjs/blog-generator-ui/.env`
2. Set the flag to `true` and leave a note in your deployment run-book:

   ```bash
   NEXT_PUBLIC_ENABLE_VERBOSE_LOGGING=true
   ```

3. Restart the Next.js server (and redeploy if this is a hosted environment) so the updated flag is picked up.
4. Confirm the change by checking the browser console or server logs—verbose entries will now include SSE connection lifecycle events and blog generation payload metadata.

## Operational Considerations

- **Performance:** Expect slightly larger log payloads and higher CPU usage in the browser console when the flag is enabled. Avoid leaving it on for long-running production deployments.
- **Security:** The additional logs may include partial blog content or job identifiers. Ensure you have approval before enabling verbose logging in customer-facing environments.
- **Version Control:** The `.env` files are tracked in this repository. Update them responsibly and coordinate with the DevOps team before committing changes that affect shared environments.

## Disabling After Use

Simply reset the flag to `false` (or remove the line entirely) and restart the services. The guard in `src/lib/logger/env.ts` will revert to production-safe logging automatically.
