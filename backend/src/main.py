"""
CrewAI Blog Generation Service - Real-time WebSocket API

This Flask application provides a REST API with WebSocket support for generating blog posts
using CrewAI Flows. It uses a structured workflow approach with explicit control points
to send meaningful, business-relevant status updates to connected frontend clients.

Key Features:
- Asynchronous blog generation using CrewAI Flows
- Real-time progress updates via WebSockets
- Structured workflow with explicit control points
- Business-relevant status messages
- Status tracking for multiple concurrent tasks

Architecture:
1. REST endpoint accepts blog generation requests
2. Background thread executes CrewAI Flow-based blog generation
3. Flow sends custom status updates at each workflow phase
4. WebSocket streams real-time updates to frontend
5. Task completion triggers final status update with generated content
"""

from datetime import datetime
from flask import Flask, request as flask_request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
from bloggen.flows import BlogGenerationFlow  # New Flow-based approach
import os
import threading
import uuid
import time
import logging

# Load environment variables for CrewAI configuration
from bloggen.helper import load_env
load_env()

# Initialize Flask application with CORS and WebSocket support
app = Flask(__name__)
CORS(app, origins="*")  # Allow all origins for development
socketio = SocketIO(app, cors_allowed_origins="*")

# Global storage for tracking active blog generation tasks
# Structure: {task_id: {id, topic, status, created_at, current_step, result, error}}
active_tasks = {}

# Configure logging to capture CrewAI output
logging.basicConfig(level=logging.INFO)

def background_blog_generation(task_id, topic, room_id):
    """
    Background task that executes CrewAI Flow-based blog generation with real-time progress tracking.
    
    This function runs in a separate thread to prevent blocking the main Flask application.
    It uses CrewAI Flows to orchestrate the blog generation process through structured phases,
    sending meaningful business-relevant status updates to the frontend via WebSockets.
    
    Process Flow:
    1. Initialize BlogGenerationFlow with WebSocket communication
    2. Execute structured workflow: Research → Content → Fact-check → Finalize
    3. Stream meaningful progress updates at each phase
    4. Send completion status and generated content to frontend
    5. Handle errors gracefully with user-friendly messages
    
    Args:
        task_id (str): Unique identifier for this generation task
        topic (str): Blog topic provided by the user
        room_id (str): WebSocket room ID for broadcasting updates
    """
    try:
        # === TASK INITIALIZATION ===
        # Update the task record with in-progress status
        active_tasks[task_id]['status'] = 'in_progress'
        active_tasks[task_id]['current_step'] = 'Initializing blog generation workflow...'
        
        # Send initial status update to frontend
        socketio.emit('status_update', {
            'task_id': task_id,
            'status': 'in_progress',
            'message': 'Initializing blog generation workflow...',
            'step': 0,
            'total_steps': 4
        }, to=room_id)
        
        # Send initial log update
        socketio.emit('log_update', {
            'task_id': task_id,
            'log': f'🚀 Blog generation started for topic: "{topic}"',
            'timestamp': datetime.now().isoformat()
        }, to=room_id)
        
        # === FLOW EXECUTION ===
        # Create and configure the blog generation flow
        blog_flow = BlogGenerationFlow(
            socketio=socketio,
            task_id=task_id,
            room_id=room_id
        )
        
        # Prepare input parameters for the flow
        flow_inputs = {
            'topic': topic,
            'current_year': str(datetime.now().year)
        }
        
        # Execute the structured blog generation workflow
        print(f"[DEBUG] Starting CrewAI Flow execution for task {task_id}")
        print(f"[DEBUG] Flow inputs: {flow_inputs}")
        
        # Send log update about Flow execution start
        socketio.emit('log_update', {
            'task_id': task_id,
            'log': '🌊 CrewAI Flow execution started',
            'timestamp': datetime.now().isoformat()
        }, to=room_id)
        
        # The flow will handle all status updates internally through its phases
        # Execute the complete flow using kickoff method (this will run all @start and @listen methods)
        final_blog_content = blog_flow.kickoff(inputs=flow_inputs)
        
        print(f"[DEBUG] CrewAI Flow execution completed for task {task_id}")
        
        # Send final log update
        socketio.emit('log_update', {
            'task_id': task_id,
            'log': '✅ CrewAI Flow execution completed successfully',
            'timestamp': datetime.now().isoformat()
        }, to=room_id)
        
        # === COMPLETION HANDLING ===
        # Update task record with final results
        active_tasks[task_id]['status'] = 'completed'
        active_tasks[task_id]['result'] = str(final_blog_content)
        active_tasks[task_id]['completed_at'] = datetime.now().isoformat()
        active_tasks[task_id]['current_step'] = 'Blog generation completed successfully!'
        
        # Send final completion event with generated content
        socketio.emit('generation_complete', {
            'task_id': task_id,
            'status': 'completed',
            'message': 'Blog generation completed successfully!',
            'content': str(final_blog_content)
        }, to=room_id)
        
    except Exception as e:
        # === ERROR HANDLING ===
        # Update task record with error information
        active_tasks[task_id]['status'] = 'failed'
        active_tasks[task_id]['error'] = str(e)
        active_tasks[task_id]['completed_at'] = datetime.now().isoformat()
        active_tasks[task_id]['current_step'] = f'Error: {str(e)}'
        
        # Notify frontend of the error
        socketio.emit('generation_error', {
            'task_id': task_id,
            'status': 'failed',
            'error': str(e),
            'message': 'Blog generation failed. Please try again.'
        }, to=room_id)
        
        # Log error for debugging
        logging.error(f"Blog generation failed for task {task_id}: {e}")
        print(f"[ERROR] Blog generation failed for task {task_id}: {e}")


# =============================================================================
# REST API ENDPOINTS
# =============================================================================

@app.route('/generate-blog', methods=['POST'])
def generate_blog():
    """
    Main API endpoint to initiate blog generation using CrewAI Flows.
    
    This endpoint:
    1. Validates the incoming request for required topic parameter
    2. Creates a new task record with unique ID
    3. Starts background thread for CrewAI Flow-based execution
    4. Returns task information for frontend tracking
    
    The Flow-based approach provides structured workflow phases:
    - Research Phase: Gather insights and data on the topic
    - Content Generation: Create engaging blog content
    - Fact Checking: Verify accuracy and credibility
    - Finalization: Polish and format for publication
    
    Each phase sends meaningful status updates via WebSocket.
    
    Request Body:
        {
            "topic": "Your blog topic here"
        }
    
    Response:
        {
            "task_id": "uuid-string",
            "status": "queued", 
            "message": "Blog generation started..."
        }
    """
    # Validate request data
    data = flask_request.json
    if not data or 'topic' not in data:
        return jsonify({'error': 'Topic is required'}), 400
    
    topic = data.get('topic')
    
    # Generate unique task identifier
    task_id = str(uuid.uuid4())
    
    # Create task record for tracking
    active_tasks[task_id] = {
        'id': task_id,
        'topic': topic,
        'status': 'queued',
        'created_at': datetime.now().isoformat(),
        'current_step': 'Queued for processing',
        'result': None,
        'error': None
    }
    
    # Start background blog generation in separate thread
    thread = threading.Thread(
        target=background_blog_generation,
        args=(task_id, topic, task_id)  # Using task_id as WebSocket room_id
    )
    thread.daemon = True  # Thread will die when main program exits
    thread.start()
    
    # Return task information to frontend
    return jsonify({
        'task_id': task_id,
        'status': 'queued',
        'message': 'Blog generation started. Connect to WebSocket for real-time updates.'
    }), 202

@app.route('/task-status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """
    Get the current status of a specific blog generation task.
    
    This endpoint allows frontend clients to check task progress
    without requiring WebSocket connection.
    
    Args:
        task_id (str): The unique task identifier
        
    Response:
        {
            "id": "task-id",
            "topic": "Blog topic",
            "status": "queued|in_progress|completed|failed",
            "created_at": "ISO timestamp",
            "current_step": "Human readable status",
            "result": "Generated blog content (if completed)",
            "error": "Error message (if failed)"
        }
    """
    if task_id not in active_tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    return jsonify(active_tasks[task_id]), 200

@app.route('/tasks', methods=['GET'])
def get_all_tasks():
    """
    Get all tasks for debugging and monitoring purposes.
    
    This endpoint is primarily used for:
    - Development debugging
    - System monitoring
    - Administrative oversight
    
    Response:
        [
            {task_record_1},
            {task_record_2},
            ...
        ]
    """
    return jsonify(list(active_tasks.values())), 200


# =============================================================================
# WEBSOCKET EVENT HANDLERS
# =============================================================================
@socketio.on('connect')
def handle_connect():
    """
    Handle new WebSocket connections.
    
    This event fires when a frontend client establishes a WebSocket connection.
    It sends a confirmation message to let the client know the connection is active.
    """
    print("Client connected")
    emit('connected', {'message': 'Connected to blog generation service'})

@socketio.on('disconnect')
def handle_disconnect():
    """
    Handle WebSocket disconnections.
    
    This event fires when a frontend client closes their WebSocket connection.
    Used primarily for logging and cleanup if needed.
    """
    print("Client disconnected")

@socketio.on('join_task')
def handle_join_task(data):
    """
    Handle client requests to join a specific task room.
    
    This allows frontend clients to subscribe to updates for a specific blog
    generation task. Each task has its own "room" for targeted message delivery.
    
    Expected data:
        {
            "task_id": "uuid-string"
        }
    
    Args:
        data (dict): WebSocket event data containing task_id
    """
    task_id = data.get('task_id')
    if task_id:
        # Join the WebSocket room for this specific task
        join_room(task_id)
        emit('joined_task', {'task_id': task_id, 'message': f'Joined task {task_id}'})
        
        # Send current status if task exists (useful for reconnections)
        if task_id in active_tasks:
            emit('status_update', {
                'task_id': task_id,
                'status': active_tasks[task_id]['status'],
                'message': active_tasks[task_id]['current_step']
            })


# =============================================================================
# APPLICATION STARTUP
# =============================================================================

if __name__ == '__main__':
    """
    Start the Flask application with WebSocket support.
    
    Configuration:
    - debug=True: Enable development mode with auto-reload
    - host='0.0.0.0': Accept connections from any IP address
    - port=5000: Standard Flask development port
    
    Note: In production, this should be run through a proper WSGI server
    like Gunicorn with proper configuration for WebSocket support.
    """
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)