# Callback Error Handling Fix - Option 3D Implementation

## Summary
Fixed `AttributeError: 'TaskStartedEvent' object has no attribute 'task_id'` error by implementing robust error handling in CrewAI event callbacks.

## Problem
The callback system was attempting to access `event.task_id` as a fallback when `source.name` didn't exist, but `TaskStartedEvent` objects don't have a `task_id` attribute. This caused non-critical errors during blog generation that cluttered logs.

## Solution: Option 3D - Full Error Handling
Implemented defensive error handling that:
1. Removes dependency on `event.task_id` 
2. Uses safe fallback values (`'task'`, `'unnamed task'`)
3. Wraps handlers in try-except blocks to catch AttributeError specifically
4. Distinguishes between expected (AttributeError) and unexpected errors
5. Ensures callbacks never break the main workflow

## Changes Made

### File: `backend/src/bloggen/callbacks.py`

#### 1. Enhanced `_handle_task_started` (Lines 156-178)
**Before:**
```python
def _handle_task_started(self, context: RunContext, source, event: TaskStartedEvent) -> None:
    context.status_manager.send_status_update(
        message=f"{context.phase_name.title()} phase in progress",
        step=self._phase_step(context.phase_name),
        detail=f"Task '{getattr(source, 'name', event.task_id)}' started",  # ❌ Breaks here
    )
```

**After:**
```python
def _handle_task_started(self, context: RunContext, source, event: TaskStartedEvent) -> None:
    """
    Handle TaskStartedEvent from CrewAI.
    Defensive implementation - errors here should never break workflow.
    """
    try:
        # Try to get a meaningful task identifier
        task_name = getattr(source, 'name', None)
        if not task_name:
            task_name = getattr(source, 'description', 'task')
        
        context.status_manager.send_status_update(
            message=f"{context.phase_name.title()} phase in progress",
            step=self._phase_step(context.phase_name),
            detail=f"Task '{task_name}' started",
        )
        
    except AttributeError as e:
        # Expected error if CrewAI changes event/source structure
        logger.debug(f"Event structure changed in task started: {e}")
        
    except Exception as e:
        # Unexpected errors should be logged but not propagated
        logger.warning(f"Unexpected error in task started handler: {e}", exc_info=True)
```

#### 2. Enhanced `_handle_task_completed` (Lines 180-203)
- Added try-except wrapper
- Safe extraction of agent name with fallback
- Graceful handling of AttributeError

#### 3. Enhanced `_handle_task_failed` (Lines 205-231)
- Added try-except wrapper
- Safe error message extraction
- Fallback to generic error message if attribute access fails
- Silent failure for worst-case scenarios

#### 4. Enhanced `_with_context` (Lines 274-296)
**Before:**
```python
def _with_context(self, source: Any, event: Any, handler: Callable) -> None:
    context = self._resolve_context(source, event)
    if not context:
        return
    try:
        handler(context, source, event)
    except Exception as exc:
        logger.exception("Error processing CrewAI event %s: %s", type(event).__name__, exc)
```

**After:**
```python
def _with_context(self, source: Any, event: Any, handler: Callable) -> None:
    """
    Wrap handler with context - callbacks must never break workflow.
    Enhanced error handling distinguishes between expected and unexpected errors.
    """
    context = self._resolve_context(source, event)
    if not context:
        return
    try:
        handler(context, source, event)
    except AttributeError as exc:
        # Common issue with CrewAI event structure changes
        logger.warning(
            f"Event structure mismatch in {handler.__name__} "
            f"for {type(event).__name__}: {exc}"
        )
    except Exception as exc:
        # Catch all other unexpected errors
        logger.error(
            f"Unexpected error in {handler.__name__} "
            f"for {type(event).__name__}: {exc}",
            exc_info=True
        )
```

## Benefits

✅ **Robust**: Callbacks cannot break the main blog generation workflow
✅ **Informative**: Clear logging distinguishes expected vs unexpected errors
✅ **Maintainable**: Easy to understand error handling pattern
✅ **Future-proof**: Won't break if CrewAI changes event structure again
✅ **Production-ready**: Defensive coding suitable for production environments

## Testing

### Expected Behavior After Fix:

1. **No AttributeError exceptions** in logs during blog generation
2. **Warning logs** for event structure mismatches (debug level for AttributeError)
3. **Blog generation completes successfully** even if callbacks encounter errors
4. **Status updates continue to work** for events that don't have structure issues

### Test Commands:

```bash
# 1. Restart backend to load changes
cd backend
source .venv/bin/activate
python src/main.py

# 2. Generate a blog via frontend

# 3. Check logs for:
#    - No AttributeError exceptions
#    - Possible WARNING logs about event structure (expected)
#    - Successful blog generation completion
```

## Impact

- **Non-breaking change**: Existing functionality unchanged
- **Error suppression**: AttributeError no longer propagates from callbacks
- **Log clarity**: Better distinction between expected and unexpected errors
- **Workflow stability**: Callbacks guaranteed to not break blog generation

## Related Issues

- Original error: `'TaskStartedEvent' object has no attribute 'task_id'`
- Root cause: CrewAI library API changes in event structure
- Solution category: Defensive programming / Graceful degradation

## Date
October 19, 2025

## Author
AI Assistant (Option 3D implementation)
