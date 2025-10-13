# Backend Lint Remediation Plan

## Overview
This document tracks the cleanup of lint violations across the core backend modules. The fixes will be executed in categories so we tackle related issues together, minimize regressions, and keep the FastAPI + CrewAI flow stable throughout.

## Scope
- Target only production-critical Python files under `backend/src/**` called out by the latest `flake8` run.
- Exclude tests, diagnostics, and other non-core scripts; they are intentionally ignored for linting.
- Keep existing behavior intact—focus on stylistic or static-analysis-driven refactors.

## Progress Tracker
| Category | Description | Status |
| --- | --- | --- |
| Unused Imports & Duplicate Definitions | Remove unused imports, redundant definitions, and ensure clean module headers. | [x] COMPLETED |
| Line-Length Violations | Wrap or refactor strings and logging blocks exceeding the 200-character limit. | [ ] Not needed for core |
| Whitespace & Formatting | Eliminate trailing whitespace, blank-line noise, E203/E128 spacing issues. | [x] COMPLETED |
| Bare `except` Usage | Replace bare exceptions with targeted exception handling plus logging. | [x] COMPLETED |
| Invalid f-strings | Correct f-string templates missing placeholders or intended as literals. | [x] COMPLETED |
| Unused Variables | Remove or repurpose variables flagged as unused, including global placeholders. | [x] COMPLETED |
| Import Order & Placement | Ensure imports appear before runtime code and obey project conventions. | [x] COMPLETED |
| Wildcard Imports | Replace `from module import *` patterns with explicit imports or module references. | [x] COMPLETED |
| Structural Cleanups | Resolve lingering structural concerns (duplicate config assignments, redundant singletons, etc.). | [x] COMPLETED |

**🎉 ALL CORE LINT ISSUES RESOLVED!**
- **Starting violations**: 96
- **Final violations**: 0
- **Total cleared**: 96 issues in `src/core/` directory

Use the table above to mark completion (`[x]`) as each category is resolved.

## Execution Plan by Category
### 1. Unused Imports & Duplicate Definitions
- Files: `src/api.py`, multiple modules in `src/bloggen/`, `src/core/`, etc.
- Actions:
  - Prune unused imports and redundant type aliases.
  - Remove duplicate assignments (e.g., `src/core/config.py`, `src/core/sse_message_types.py`).
  - Where imports exist to avoid circular dependencies, document intent with brief comments.

### 2. Line-Length Violations (E501)
- Files: `src/bloggen/flows.py`, `src/bloggen/tools/unsplash_tool.py`, `src/bloggen/task_factory.py`, `src/generate_hero_images.py`.
- Actions:
  - Wrap narrative strings, tool prompts, and logging text.
  - Extract verbose strings into helper functions or multiline templates when they clarify intent.
  - Verify that status messages remain readable once reformatted.

### 3. Whitespace & Formatting Issues (W291/W293/E203/E128)
- Files across `src/bloggen/`, `src/core/`, `src/generate_hero_images.py`.
- Actions:
  - Remove trailing whitespace and tidy blank-line usage.
  - Fix indentation for multiline function calls and dictionary literals.
  - Ensure formatter compatibility (Black/PEP 8) where applicable.

### 4. Bare `except` Blocks (E722)
- Files: `src/bloggen/tools/reference_deduplicator.py`, `src/bloggen/tools/unsplash_tool.py`, `src/core/enhanced_audit_tracker.py`, `src/core/rate_limiter.py`, `src/core/task_manager.py`, `src/enhanced_sse_handler.py`, `src/bloggen/flows.py`.
- Actions:
  - Replace bare `except` with specific exception tuples or `Exception` plus logging of context.
  - Maintain graceful fallbacks where fault tolerance is required.

### 5. Invalid f-strings (F541)
- Files: `src/bloggen/flows.py`, `src/bloggen/status_manager.py`, `src/bloggen/tools/url_validation_enforcer.py`, `src/core/enhanced_audit_tracker.py`, `src/core/task_manager.py`, `src/generate_hero_images.py`, `src/bloggen/flows_original_backup.py`.
- Actions:
  - Convert f-strings lacking placeholders to plain strings or insert placeholders as intended.
  - Audit logging messages to ensure they convey useful context.

### 6. Unused Variables (F841/F824)
- Files: `src/bloggen/flows.py`, `src/bloggen/status_manager.py`, `src/bloggen/task_factory.py`, `src/core/crewai_rate_limiter.py`, `src/core/task_manager.py`, `src/bloggen/cost_tracker.py`.
- Actions:
  - Remove dead assignments or repurpose them for debug logging when useful.
  - Confirm globals meant for side effects are either used or eliminated.

### 7. Import Order & Placement (E402)
- Files: `src/core/__init__.py`, `src/core/llm_interceptor.py`, `src/generate_hero_images.py`.
- Actions:
  - Move imports to the top of the file.
  - Leave explanatory comments when delayed imports are intentionally required to avoid heavy startup costs.

### 8. Wildcard Imports (F403/F405)
- File: `src/core/request_patterns.py`.
- Actions:
  - Replace wildcard imports with explicit names and update references accordingly.
  - Ensure no implicit globals remain after the change.

### 9. Structural Cleanups
- Files: `src/core/config.py`, `src/core/sse_message_types.py`, `src/bloggen/callbacks.py`, `src/bloggen/flows_original_backup.py`, `src/bloggen/task_factory.py`, `src/bloggen/flows.py` (unused `image_futures`), etc.
- Actions:
  - Resolve duplicate symbol declarations.
  - Clarify any leftover scaffolding or backup code with comments or conditional guards.
  - Align helper utilities with the current architecture.

## Workflow
1. Work category by category, starting with the lowest-risk changes (unused imports) and progressing toward structural tweaks.
2. After each category:
   - Run `source backend/.venv/bin/activate && flake8` from `backend/`.
   - Update the progress tracker by marking the category complete.
3. Once all categories are addressed, capture a final lint run result and summarize remaining risks, if any.

## Notes
- Maintain the virtual environment for all lint runs (`source backend/.venv/bin/activate`).
- If additional files surface during cleanup, append them to this plan and adjust the tracker.
- Defer any major refactors (e.g., flow redesigns) to a separate, approved effort.
