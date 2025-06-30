from datetime import datetime
from flask import Flask, request as flask_request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
from bloggen.main import run  # Import the run function from main.py
import os
import threading
import uuid
import time
import logging
import re

#load environment variables
from bloggen.helper import load_env
load_env()

app = Flask(__name__)
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active generation tasks
active_tasks = {}

# Configure logging
logging.basicConfig(level=logging.INFO)

def background_blog_generation(task_id, topic, room_id):
    """Background task to generate blog content"""
    try:
        # Update task status
        active_tasks[task_id]['status'] = 'in_progress'
        active_tasks[task_id]['current_step'] = 'Starting blog generation...'
        
        # Emit status update
        socketio.emit('status_update', {
            'task_id': task_id,
            'status': 'in_progress',
            'message': 'Starting blog generation...',
            'step': 1,
            'total_steps': 4
        }, to=room_id)
        
        # Prepare inputs for the run function
        inputs = {
            'topic': topic,
            'current_year': str(datetime.now().year)
        }
        
        # Simple CrewAI Log Interceptor - focused on actual CrewAI patterns
        class CrewAILogInterceptor(logging.Handler):
            def __init__(self, task_id, room_id, socketio, active_tasks):
                super().__init__()
                self.task_id = task_id
                self.room_id = room_id
                self.socketio = socketio
                self.active_tasks = active_tasks
                self.current_step = 1
                self.total_steps = 4
                self.current_agent = None
                self.last_status_time = time.time()

            def emit(self, record):
                try:
                    message = record.getMessage()
                    
                    # Check for agent start pattern: # Agent: [Name]
                    agent_match = re.search(r'^#\s+Agent:\s+(.+)', message)
                    if agent_match:
                        agent_name = agent_match.group(1).strip()
                        self.current_agent = agent_name
                        self._send_status_update(f'{agent_name} is working...', self.current_step)
                        return
                    
                    # Check for tool usage: ## Using tool: [Tool Name]
                    tool_match = re.search(r'^##\s+Using tool:\s+(.+)', message)
                    if tool_match:
                        tool_name = tool_match.group(1).strip()
                        agent_info = f" ({self.current_agent})" if self.current_agent else ""
                        self._send_status_update(f'Using {tool_name}{agent_info}', self.current_step)
                        return
                    
                    # Check for crew/task execution markers
                    if '🚀 Crew: crew' in message:
                        self.current_step += 1
                        if self.current_step <= self.total_steps:
                            self._send_status_update(f'Processing step {self.current_step}...', self.current_step)
                        return
                    
                    # Check for task markers
                    if '├── 📋 Task:' in message:
                        self._send_status_update('Executing task...', self.current_step)
                        return
                        
                except Exception as e:
                    print(f"Error in log interceptor: {e}")

            def _send_status_update(self, message, step):
                """Send status update to frontend"""
                current_time = time.time()
                
                # Throttle updates (max one per second)
                if current_time - self.last_status_time < 1:
                    return
                
                self.last_status_time = current_time
                
                # Update task status
                self.active_tasks[self.task_id]['current_step'] = message
                
                # Emit to frontend
                self.socketio.emit('status_update', {
                    'task_id': self.task_id,
                    'status': 'in_progress',
                    'message': message,
                    'step': min(step, self.total_steps),
                    'total_steps': self.total_steps
                }, to=self.room_id)
        
        # Setup simple log capture
        log_interceptor = CrewAILogInterceptor(task_id, room_id, socketio, active_tasks)
        log_interceptor.setLevel(logging.INFO)  # Set to INFO level
        
        # Only add to root logger - CrewAI uses print statements that go to root
        root_logger = logging.getLogger()
        root_logger.addHandler(log_interceptor)
        root_logger.setLevel(logging.INFO)
        
        try:
            # Initial status
            active_tasks[task_id]['current_step'] = 'Starting blog generation...'
            socketio.emit('status_update', {
                'task_id': task_id,
                'status': 'in_progress',
                'message': 'Starting blog generation...',
                'step': 1,
                'total_steps': 4
            }, to=room_id)
            
            # Call the run function - real CrewAI execution
            print(f"[DEBUG] Starting CrewAI execution for task {task_id}")
            content = run(inputs)
            print(f"[DEBUG] CrewAI execution completed for task {task_id}")
            
            # Completion
            active_tasks[task_id]['current_step'] = 'Blog generation completed!'
            socketio.emit('status_update', {
                'task_id': task_id,
                'status': 'in_progress', 
                'message': 'Blog generation completed!',
                'step': 4,
                'total_steps': 4
            }, to=room_id)
            
            # Update task with results
            active_tasks[task_id]['status'] = 'completed'
            active_tasks[task_id]['result'] = content
            active_tasks[task_id]['completed_at'] = datetime.now().isoformat()
            
            # Emit completion status
            socketio.emit('generation_complete', {
                'task_id': task_id,
                'status': 'completed',
                'message': 'Blog generation completed successfully!',
                'content': content
            }, to=room_id)
            
        finally:
            # Remove the log interceptor from root logger only
            logging.getLogger().removeHandler(log_interceptor)
            
    except Exception as e:
        # Update task with error
        active_tasks[task_id]['status'] = 'failed'
        active_tasks[task_id]['error'] = str(e)
        active_tasks[task_id]['completed_at'] = datetime.now().isoformat()
        
        # Emit error status
        socketio.emit('generation_error', {
            'task_id': task_id,
            'status': 'failed',
            'error': str(e)
        }, to=room_id)
        
        logging.error(f"Blog generation failed for task {task_id}: {e}")

@app.route('/generate-blog', methods=['POST'])
def generate_blog():
    data = flask_request.json
    if not data or 'topic' not in data:
        return jsonify({'error': 'Topic is required'}), 400
    
    topic = data.get('topic')
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Create task record
    active_tasks[task_id] = {
        'id': task_id,
        'topic': topic,
        'status': 'queued',
        'created_at': datetime.now().isoformat(),
        'current_step': 'Queued for processing',
        'result': None,
        'error': None
    }
    
    # Start background task
    thread = threading.Thread(
        target=background_blog_generation,
        args=(task_id, topic, task_id)  # Using task_id as room_id
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'task_id': task_id,
        'status': 'queued',
        'message': 'Blog generation started. Connect to WebSocket for real-time updates.'
    }), 202

@app.route('/task-status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get the current status of a generation task"""
    if task_id not in active_tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    return jsonify(active_tasks[task_id]), 200

@app.route('/tasks', methods=['GET'])
def get_all_tasks():
    """Get all tasks (for debugging/monitoring)"""
    return jsonify(list(active_tasks.values())), 200

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    print("Client connected")
    emit('connected', {'message': 'Connected to blog generation service'})

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

@socketio.on('join_task')
def handle_join_task(data):
    """Join a specific task room to receive updates"""
    task_id = data.get('task_id')
    if task_id:
        join_room(task_id)
        emit('joined_task', {'task_id': task_id, 'message': f'Joined task {task_id}'})
        
        # Send current status if task exists
        if task_id in active_tasks:
            emit('status_update', {
                'task_id': task_id,
                'status': active_tasks[task_id]['status'],
                'message': active_tasks[task_id]['current_step']
            })

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)