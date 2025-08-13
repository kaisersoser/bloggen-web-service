# Backend FastAPI endpoint addition for active tasks
# This should be added to the main.py file in the backend

# Add this endpoint after the existing /tasks/{task_id} endpoint:

@app.get("/tasks/active")
async def get_active_tasks(user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get all active tasks for the current user."""
    user_tasks = []
    
    for task_id, task_data in active_tasks.items():
        # Check if user owns this task
        if task_data.get('user_id') == user.id:
            user_tasks.append({
                "id": task_id,
                "topic": task_data.get('topic', ''),
                "status": task_data.get('status', 'queued'),
                "created_at": task_data.get('created_at', ''),
                "current_step": task_data.get('current_step', ''),
                "result": task_data.get('result'),
                "error": task_data.get('error'),
                "user_id": task_data.get('user_id', ''),
                "user_email": task_data.get('user_email', ''),
                "user_role": task_data.get('user_role', '')
            })
    
    return {"tasks": user_tasks}

# This endpoint should be placed around line 360 in main.py after the /tasks/{task_id} endpoint
