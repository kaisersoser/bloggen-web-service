"""
CrewAI Blog Generation Service - Real-time WebSocket API

This Flask application provides a REST API with WebSocket support for generating blog posts
using CrewAI agents. It captures real-time progress updates from CrewAI execution and streams
them to connected frontend clients.

Key Features:
- Asynchronous blog generation using CrewAI
- Real-time progress updates via WebSockets
- Log interception to track agent activities
- Status tracking for multiple concurrent tasks

Architecture:
1. REST endpoint accepts blog generation requests
2. Background thread executes CrewAI blog generation
3. Custom log handler intercepts CrewAI output
4. WebSocket streams real-time updates to frontend
5. Task completion triggers final status update
"""

from datetime import datetime
from flask import Flask, request as flask_request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
from bloggen.main import run  # CrewAI blog generation function
import os
import threading
import uuid
import time
import logging
import re

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
    Background task that executes CrewAI blog generation with real-time progress tracking.
    
    This function runs in a separate thread to prevent blocking the main Flask application.
    It sets up log interception to capture CrewAI agent activities and streams progress
    updates to the frontend via WebSockets.
    
    Process Flow:
    1. Initialize task status and send initial update
    2. Set up CrewAI log interceptor for real-time monitoring
    3. Execute CrewAI blog generation with input parameters
    4. Stream progress updates as agents work through tasks
    5. Send completion status and generated content to frontend
    6. Clean up log handlers and update task records
    
    Args:
        task_id (str): Unique identifier for this generation task
        topic (str): Blog topic provided by the user
        room_id (str): WebSocket room ID for broadcasting updates
    """
    try:
        # === TASK INITIALIZATION ===
        # Update the task record with in-progress status
        active_tasks[task_id]['status'] = 'in_progress'
        active_tasks[task_id]['current_step'] = 'Starting blog generation...'
        
        # Send initial status update to frontend
        socketio.emit('status_update', {
            'task_id': task_id,
            'status': 'in_progress',
            'message': 'Starting blog generation...',
            'step': 1,
            'total_steps': 4
        }, to=room_id)
        
        # === CREWAI INPUT PREPARATION ===
        # Prepare input parameters for CrewAI blog generation
        inputs = {
            'topic': topic,
            'current_year': str(datetime.now().year)
        }
        
        # === CREWAI LOG INTERCEPTOR SETUP ===
        # Custom logging handler that captures and parses CrewAI output in real-time
        class CrewAILogInterceptor(logging.Handler):
            """
            Custom logging handler that intercepts CrewAI log messages and converts them
            into structured status updates for the frontend.
            
            This handler specifically looks for CrewAI's output patterns:
            - Agent activities: "# Agent: [Name]"
            - Tool usage: "## Using tool: [Tool Name]" 
            - Task execution: "🚀 Crew: crew" and "├── 📋 Task:"
            
            When these patterns are detected, it sends real-time status updates
            to the frontend via WebSockets.
            """
            
            def __init__(self, task_id, room_id, socketio, active_tasks):
                """
                Initialize the log interceptor with WebSocket communication setup.
                
                Args:
                    task_id (str): Task ID for status updates
                    room_id (str): WebSocket room for broadcasting
                    socketio: Flask-SocketIO instance for real-time communication
                    active_tasks (dict): Reference to global task storage
                """
                super().__init__()
                self.task_id = task_id
                self.room_id = room_id
                self.socketio = socketio
                self.active_tasks = active_tasks
                self.current_step = 1
                self.total_steps = 4
                self.current_agent = None  # Track which agent is currently active
                self.last_status_time = time.time()  # For throttling updates

            def emit(self, record):
                """
                Process each log record and extract CrewAI progress information.
                
                This method analyzes log messages using regex patterns to identify:
                1. Agent start activities 
                2. Tool usage by agents
                3. Task execution milestones
                4. Crew workflow progression
                
                Args:
                    record (LogRecord): Python logging record containing the message
                """
                try:
                    message = record.getMessage()
                    
                    # === AGENT ACTIVITY DETECTION ===
                    # Pattern: "# Agent: Senior Researcher" (agent starts working)
                    agent_match = re.search(r'^#\s+Agent:\s+(.+)', message)
                    if agent_match:
                        agent_name = agent_match.group(1).strip()
                        self.current_agent = agent_name
                        self._send_status_update(f'{agent_name} is working...', self.current_step)
                        return
                    
                    # === TOOL USAGE DETECTION ===
                    # Pattern: "## Using tool: Search the internet with Serper"
                    tool_match = re.search(r'^##\s+Using tool:\s+(.+)', message)
                    if tool_match:
                        tool_name = tool_match.group(1).strip()
                        agent_info = f" ({self.current_agent})" if self.current_agent else ""
                        self._send_status_update(f'Using {tool_name}{agent_info}', self.current_step)
                        return
                    
                    # === CREW WORKFLOW PROGRESSION ===
                    # Pattern: "🚀 Crew: crew" (major workflow milestone)
                    if '🚀 Crew: crew' in message:
                        self.current_step += 1
                        if self.current_step <= self.total_steps:
                            self._send_status_update(f'Processing step {self.current_step}...', self.current_step)
                        return
                    
                    # === TASK EXECUTION DETECTION ===
                    # Pattern: "├── 📋 Task:" (individual task within workflow)
                    if '├── 📋 Task:' in message:
                        self._send_status_update('Executing task...', self.current_step)
                        return
                        
                except Exception as e:
                    print(f"Error in log interceptor: {e}")

            def _send_status_update(self, message, step):
                """
                Send a status update to the frontend via WebSocket.
                
                This method handles:
                1. Update throttling (max 1 update per second)
                2. Task record updates
                3. WebSocket emission to connected clients
                
                Args:
                    message (str): Human-readable status message
                    step (int): Current progress step (1-4)
                """
                current_time = time.time()
                
                # Throttle updates to prevent overwhelming the frontend
                if current_time - self.last_status_time < 1:
                    return
                
                self.last_status_time = current_time
                
                # Update the global task record
                self.active_tasks[self.task_id]['current_step'] = message
                
                # Broadcast status update to connected frontend clients
                self.socketio.emit('status_update', {
                    'task_id': self.task_id,
                    'status': 'in_progress',
                    'message': message,
                    'step': min(step, self.total_steps),
                    'total_steps': self.total_steps
                }, to=self.room_id)
        
        # === LOG HANDLER SETUP ===
        # Create and configure the custom log interceptor
        log_interceptor = CrewAILogInterceptor(task_id, room_id, socketio, active_tasks)
        log_interceptor.setLevel(logging.INFO)  # Capture INFO level and above
        
        # Attach to root logger since CrewAI uses print statements that route here
        root_logger = logging.getLogger()
        root_logger.addHandler(log_interceptor)
        root_logger.setLevel(logging.INFO)
        
        try:
            # === CREWAI EXECUTION ===
            # Send initial status before starting CrewAI
            active_tasks[task_id]['current_step'] = 'Starting blog generation...'
            socketio.emit('status_update', {
                'task_id': task_id,
                'status': 'in_progress',
                'message': 'Starting blog generation...',
                'step': 1,
                'total_steps': 4
            }, to=room_id)
            
            # Execute CrewAI blog generation (this is where the magic happens)
            print(f"[DEBUG] Starting CrewAI execution for task {task_id}")
            content = run(inputs)  # CrewAI execution with real-time log capture
            print(f"[DEBUG] CrewAI execution completed for task {task_id}")
            
            # === COMPLETION HANDLING ===
            # Update task status to show completion
            active_tasks[task_id]['current_step'] = 'Blog generation completed!'
            socketio.emit('status_update', {
                'task_id': task_id,
                'status': 'in_progress', 
                'message': 'Blog generation completed!',
                'step': 4,
                'total_steps': 4
            }, to=room_id)
            
            # Update task record with final results
            active_tasks[task_id]['status'] = 'completed'
            active_tasks[task_id]['result'] = content
            active_tasks[task_id]['completed_at'] = datetime.now().isoformat()
            
            # Send final completion event with generated content
            socketio.emit('generation_complete', {
                'task_id': task_id,
                'status': 'completed',
                'message': 'Blog generation completed successfully!',
                'content': content
            }, to=room_id)
            
        finally:
            # === CLEANUP ===
            # Always remove the log handler to prevent memory leaks
            logging.getLogger().removeHandler(log_interceptor)
            
    except Exception as e:
        # === ERROR HANDLING ===
        # Update task record with error information
        active_tasks[task_id]['status'] = 'failed'
        active_tasks[task_id]['error'] = str(e)
        active_tasks[task_id]['completed_at'] = datetime.now().isoformat()
        
        # Notify frontend of the error
        socketio.emit('generation_error', {
            'task_id': task_id,
            'status': 'failed',
            'error': str(e)
        }, to=room_id)
        
        # Log error for debugging
        logging.error(f"Blog generation failed for task {task_id}: {e}")


# =============================================================================
# REST API ENDPOINTS
# =============================================================================

@app.route('/generate-blog', methods=['POST'])
def generate_blog():
    """
    Main API endpoint to initiate blog generation.
    
    This endpoint:
    1. Validates the incoming request for required topic parameter
    2. Creates a new task record with unique ID
    3. Starts background thread for CrewAI execution
    4. Returns task information for frontend tracking
    
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