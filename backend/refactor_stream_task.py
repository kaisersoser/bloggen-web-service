#!/usr/bin/env python3
"""
Script to refactor stream_task function in main.py for Phase 3.3.
Replaces 511-line function with clean SSEHandler delegation.
"""

import re

# Read the current main.py
with open('/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/src/main.py', 'r') as f:
    content = f.read()

# Find the stream_task function (starts at line ~769, ends before delete_task at ~1280)
# We'll use a regex to find the entire function

# Pattern to match the stream_task function
pattern = r'(@app\.get\("/stream/\{task_id\}"\)\s+async def stream_task\(task_id: str, token: str\):.*?)(@app\.delete\("/tasks/\{task_id\}"\))'

# New implementation
new_stream_task = '''@app.get("/stream/{task_id}")
async def stream_task(task_id: str, token: str):
    """
    SSE stream for a specific task with Redis pub/sub support.
    
    Phase 3.3: Refactored to use dedicated SSEHandler service for maintainability.
    Reduced from 511 lines to ~50 lines by extracting streaming logic.
    """
    # Authenticate via query token
    user = await get_current_user_from_query_token(token)
    
    # Check user permissions for existing tasks
    task = await task_manager.get_task(task_id)
    if task and task["user_id"] != user.id and user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Initialize SSE handler with dependencies
    sse_handler = SSEHandler(
        redis_manager=redis_manager if redis_manager else None,
        task_manager=task_manager,
        message_buffer=message_buffer if message_buffer else None,
        heartbeat_interval=15,  # seconds
        timeout_seconds=420,  # 7 minutes for complex blog generation
    )
    
    async def event_generator():
        """
        Generator function for SSE events.
        Delegates to SSEHandler for all streaming logic.
        """
        try:
            # Stream events from SSEHandler with proper error handling
            async for event in sse_handler.stream_events(
                task_id=task_id,
                user_id=user.id,
                retry_count=5,
            ):
                yield event
        
        except Exception as e:
            logger.error(
                f"❌ Error in SSE event generator for task {task_id}: {e}",
                exc_info=True,
            )
            # Send error event to client
            error_event = {
                "type": "error",
                "task_id": task_id,
                "message": f"Stream error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            }
            yield f"data: {json.dumps(error_event)}\\n\\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "X-Content-Type-Options": "nosniff",
            "Transfer-Encoding": "chunked",
        },
    )


@app.delete("/tasks/{task_id}")'''

# Replace the function
new_content = re.sub(pattern, new_stream_task, content, flags=re.DOTALL)

# Check if replacement was successful
if new_content == content:
    print("❌ No replacement made - pattern didn't match")
    print("\nSearching for stream_task function...")
    if '@app.get("/stream/{task_id}")' in content:
        print("✅ Found @app.get decorator")
    if 'async def stream_task' in content:
        print("✅ Found async def stream_task")
    if '@app.delete("/tasks/{task_id}")' in content:
        print("✅ Found @app.delete decorator")
else:
    # Write the updated content
    with open('/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/src/main.py', 'w') as f:
        f.write(new_content)
    
    # Calculate line reduction
    old_lines = content.count('\n')
    new_lines = new_content.count('\n')
    reduction = old_lines - new_lines
    
    print(f"✅ Successfully refactored stream_task function!")
    print(f"📊 Line reduction: {old_lines} → {new_lines} lines ({reduction} lines removed)")
    print(f"📈 main.py reduced by {(reduction/old_lines)*100:.1f}%")
