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
from flask import Flask, request as flask_request, jsonify, g, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
from bloggen.flows import BlogGenerationFlow  # New Flow-based approach
import os
import threading
import uuid
import json
import logging
import time
import openai

# Load environment variables for CrewAI configuration
from bloggen.helper import load_env
load_env()

# Import authentication middleware
from auth_middleware import require_auth, require_role, check_generation_limits

# Import HTTPS configuration
from https_config import get_server_config, should_use_https

# Initialize Flask application with CORS and WebSocket support
app = Flask(__name__)

# Dynamic CORS configuration for different environments
def get_cors_origins():
    """Get allowed CORS origins based on environment and deployment"""
    origins = []
    
    # Development origins (HTTPS enforced in all environments)
    dev_origins = [
        'https://localhost:3000',
        'https://localhost:3001', 
        'https://127.0.0.1:3000',
        'https://127.0.0.1:3001'
    ]
    
    # Get environment
    environment = os.getenv('ENVIRONMENT', 'development').lower()
    
    if environment == 'production':
        # Production: Only allow HTTPS domains
        frontend_url = os.getenv('FRONTEND_URL')
        if frontend_url:
            # Ensure production URLs are HTTPS
            if not frontend_url.startswith('https://'):
                logging.warning(f"Frontend URL should use HTTPS in production: {frontend_url}")
                # Convert to HTTPS if it's HTTP
                if frontend_url.startswith('http://'):
                    frontend_url = frontend_url.replace('http://', 'https://')
            origins.append(frontend_url)
        
        # Additional production domains (enforce HTTPS)
        production_domains = os.getenv('PRODUCTION_DOMAINS', '').split(',')
        for domain in production_domains:
            domain = domain.strip()
            if domain and not domain.startswith('https://yourdomain.com'):  # Skip placeholders
                # Ensure HTTPS for production domains
                if not domain.startswith('https://'):
                    if domain.startswith('http://'):
                        domain = domain.replace('http://', 'https://')
                        logging.warning(f"Converting HTTP to HTTPS for production domain: {domain}")
                    else:
                        domain = f"https://{domain}"
                origins.append(domain)
                
        # Also add NextAuth URL if different (enforce HTTPS)
        nextauth_url = os.getenv('NEXTAUTH_URL')
        if nextauth_url and nextauth_url not in origins:
            if not nextauth_url.startswith('https://'):
                if nextauth_url.startswith('http://'):
                    nextauth_url = nextauth_url.replace('http://', 'https://')
                    logging.warning(f"Converting NextAuth URL to HTTPS: {nextauth_url}")
            origins.append(nextauth_url)
            
    else:
        # Development: Also enforce HTTPS (use HTTPS localhost URLs)
        origins.extend(dev_origins)
        
        frontend_url = os.getenv('FRONTEND_URL')
        if frontend_url:
            # Convert HTTP to HTTPS even in development
            if frontend_url.startswith('http://localhost') or frontend_url.startswith('http://127.0.0.1'):
                frontend_url = frontend_url.replace('http://', 'https://')
                logging.info(f"Converting development URL to HTTPS: {frontend_url}")
            origins.append(frontend_url)
    
    # Remove duplicates and empty strings
    origins = list(set(filter(None, origins)))
    return origins

# Configure CORS
allowed_origins = get_cors_origins()
CORS(app, origins=allowed_origins, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins=allowed_origins)

# HTTPS enforcement middleware
@app.before_request
def force_https():
    """Force HTTPS in all environments"""
    # Skip HTTPS enforcement for health checks and internal requests
    if flask_request.path in ['/health', '/ping']:
        return
        
    # Check if request is using HTTPS
    if not flask_request.is_secure and not flask_request.headers.get('X-Forwarded-Proto') == 'https':
        # Allow HTTPS on localhost for development (self-signed certificates)
        if flask_request.host.startswith('localhost') or flask_request.host.startswith('127.0.0.1'):
            # Only allow HTTPS on localhost
            if not flask_request.is_secure:
                return jsonify({
                    'error': 'HTTPS Required',
                    'message': 'This API requires HTTPS. Please use https://localhost instead of http://localhost',
                    'help': 'Set up HTTPS for local development using mkcert or similar tools'
                }), 426
        else:
            # Redirect HTTP to HTTPS for non-localhost
            return jsonify({
                'error': 'HTTPS Required',
                'message': 'This API requires HTTPS. Please use https:// instead of http://'
            }), 426  # 426 Upgrade Required

# Security headers middleware
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    environment = os.getenv('ENVIRONMENT', 'development').lower()
    
    # Apply security headers in all environments
    # Strict Transport Security (HSTS)
    if environment == 'production':
        # Stronger HSTS for production
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    else:
        # Lighter HSTS for development
        response.headers['Strict-Transport-Security'] = 'max-age=3600; includeSubDomains'
    
    # Content Security Policy (adjusted for development)
    if environment == 'production':
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' wss: https:; "
            "font-src 'self' data:; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
    else:
        # More relaxed CSP for development
        response.headers['Content-Security-Policy'] = (
            "default-src 'self' https://localhost:* https://127.0.0.1:*; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://localhost:* https://127.0.0.1:*; "
            "style-src 'self' 'unsafe-inline' https://localhost:* https://127.0.0.1:*; "
            "img-src 'self' data: https: https://localhost:* https://127.0.0.1:*; "
            "connect-src 'self' wss: https: https://localhost:* https://127.0.0.1:* wss://localhost:* wss://127.0.0.1:*; "
            "font-src 'self' data: https://localhost:* https://127.0.0.1:*; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
    
    # X-Frame-Options
    response.headers['X-Frame-Options'] = 'DENY'
    
    # X-Content-Type-Options
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # X-XSS-Protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Referrer Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Permissions Policy
    response.headers['Permissions-Policy'] = (
        "camera=(), "
        "microphone=(), "
        "geolocation=(), "
        "payment=(), "
        "usb=(), "
        "magnetometer=(), "
        "accelerometer=(), "
        "gyroscope=()"
    )
    
    return response

# Log configuration for debugging
environment = os.getenv('ENVIRONMENT', 'development')
logging.info(f"Environment: {environment}")
logging.info(f"HTTPS enforcement: enabled (all environments)")
logging.info(f"Security headers: enabled (all environments)")
logging.info(f"Allowed CORS origins: {allowed_origins}")

# Global storage for tracking active blog generation tasks
# Structure: {task_id: {id, topic, status, created_at, current_step, result, error}}
active_tasks = {}

# Configure logging to capture CrewAI output
logging.basicConfig(level=logging.INFO)

def background_blog_generation(task_id, topic, room_id=None):
    """
    Background task that executes CrewAI Flow-based blog generation with real-time progress tracking.
    
    This function runs in a separate thread to prevent blocking the main Flask application.
    It uses CrewAI Flows to orchestrate the blog generation process through structured phases,
    sending meaningful business-relevant status updates via task status updates (for SSE streaming).
    
    Process Flow:
    1. Initialize BlogGenerationFlow with status update callback
    2. Execute structured workflow: Research → Content → Fact-check → Finalize
    3. Update task status at each phase (consumed by SSE stream)
    4. Store completion status and generated content
    5. Handle errors gracefully with user-friendly messages
    
    Args:
        task_id (str): Unique identifier for this generation task
        topic (str): Blog topic provided by the user
        room_id (str): Legacy parameter for Socket.IO compatibility (unused)
    """
    try:
        # === TASK INITIALIZATION ===
        
        # Update the task record with in-progress status
        if task_id in active_tasks:
            active_tasks[task_id]['status'] = 'in_progress'
            active_tasks[task_id]['current_step'] = 'Initializing blog generation workflow...'
            
            logging.info(f"🚀 Blog generation started for task {task_id} with topic: '{topic}'")
        
        # === FLOW EXECUTION ===
        # Create and configure the blog generation flow
        # Note: We use a status callback for SSE streaming instead of Socket.IO
        
        # Define status update callback for the flow
        def update_task_status(step_name, message, progress=0.5):
            """Callback function for flow to update task status and stream detailed logs"""
            if task_id in active_tasks:
                active_tasks[task_id]['current_step'] = f"{step_name}: {message}"
                # Store detailed logs for streaming
                if 'detailed_logs' not in active_tasks[task_id]:
                    active_tasks[task_id]['detailed_logs'] = []
                
                # Add timestamped log entry
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'step': step_name,
                    'message': message,
                    'progress': progress
                }
                active_tasks[task_id]['detailed_logs'].append(log_entry)
                
                # Also add the last log as current_log for immediate streaming
                active_tasks[task_id]['current_log'] = log_entry
                
                logging.info(f"Task {task_id} - {step_name}: {message}")
        
        blog_flow = BlogGenerationFlow(status_callback=update_task_status)
        
        # Prepare input parameters for the flow
        flow_inputs = {
            'topic': topic,
            'current_year': str(datetime.now().year)
        }
        
        # Execute the structured blog generation workflow
        logging.info(f"Task {task_id} - 🌊 CrewAI Flow execution started")
        
        # Update status before flow execution
        if task_id in active_tasks:
            active_tasks[task_id]['current_step'] = 'Executing CrewAI blog generation flow...'
        
        # Execute the complete flow using kickoff method
        final_blog_content = blog_flow.kickoff(inputs=flow_inputs)
        
        logging.info(f"Task {task_id} - ✅ CrewAI Flow execution completed successfully")
        
        # === COMPLETION HANDLING ===
        
        # Update task record with final results
        if task_id in active_tasks:
            active_tasks[task_id]['status'] = 'completed'
            active_tasks[task_id]['result'] = str(final_blog_content)
            active_tasks[task_id]['completed_at'] = datetime.now().isoformat()
            active_tasks[task_id]['current_step'] = 'Blog generation completed successfully!'
            
            logging.info(f"Task {task_id} completed successfully. Content length: {len(str(final_blog_content))} characters")
        
    except Exception as e:
        # === ENHANCED ERROR HANDLING ===
        from error_handler import create_error_response
        
        # Create structured error response
        error_info = create_error_response(e)
        
        # Update task record with error information
        if task_id in active_tasks:
            active_tasks[task_id]['status'] = 'failed'
            active_tasks[task_id]['error'] = str(e)
            active_tasks[task_id]['error_info'] = error_info
            active_tasks[task_id]['completed_at'] = datetime.now().isoformat()
            active_tasks[task_id]['current_step'] = f'Error: {error_info["user_message"]}'
        
        # Log error for debugging
        logging.error(f"Blog generation failed for task {task_id}: {e}")
        logging.exception("Full error details:")


# =============================================================================
# HEALTH CHECK ENDPOINTS (No authentication required)
# =============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for load balancers and monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'https_enforced': os.getenv('ENVIRONMENT', 'development').lower() == 'production'
    }), 200

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping endpoint"""
    return jsonify({'message': 'pong'}), 200

@app.route('/generate-title', methods=['POST'])
@require_auth
def generate_title():
    """
    Generate a concise blog title from blog instructions using OpenAI.
    
    This endpoint:
    1. Takes blog instructions as input
    2. Uses OpenAI to generate a short, engaging title
    3. Returns the generated title
    
    Request Body:
    {
        "instructions": "Blog instructions or description"
    }
    
    Response:
    {
        "title": "Generated Blog Title",
        "success": true
    }
    """
    try:
        # Get request data
        data = flask_request.get_json()
        if not data:
            return jsonify({
                'error': 'Request body must be JSON',
                'success': False
            }), 400
        
        # Validate required fields
        instructions = data.get('instructions', '').strip()
        if not instructions:
            return jsonify({
                'error': 'Instructions are required',
                'success': False
            }), 400
        
        # Set up OpenAI API key
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            logging.error("OpenAI API key not found in environment variables")
            return jsonify({
                'error': 'OpenAI API key not configured',
                'success': False
            }), 500
        
        # Generate title using OpenAI
        try:
            client = openai.OpenAI(api_key=openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates short, engaging blog titles. Extract the core topic from user instructions and create a concise title (5-10 words max). Remove any instruction words like 'Generate', 'Write', 'Create', 'blog about', etc. Focus only on the main subject. Return only the title, nothing else."
                    },
                    {
                        "role": "user",
                        "content": f"Extract the core topic and create a short blog title from: \"{instructions}\""
                    }
                ],
                max_tokens=25,
                temperature=0.5,
            )
            
            generated_title = response.choices[0].message.content
            if not generated_title:
                return jsonify({
                    'error': 'No title generated',
                    'success': False
                }), 500
                
            generated_title = generated_title.strip()
            
            # Clean up the title (remove quotes if present)
            clean_title = generated_title.replace('"', '').replace("'", "")
            
            # Format title with proper capitalization (Title Case)
            formatted_title = clean_title.title()
            
            # Fix common title case issues
            # Keep certain words lowercase unless they're the first word
            lowercase_words = ['a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'if', 'in', 'nor', 'of', 'on', 'or', 'so', 'the', 'to', 'up', 'yet']
            words = formatted_title.split()
            
            for i, word in enumerate(words):
                if i > 0 and word.lower() in lowercase_words:
                    words[i] = word.lower()
                elif i == 0:  # Always capitalize first word
                    words[i] = word.capitalize()
            
            final_title = ' '.join(words)
            
            return jsonify({
                'title': final_title,
                'success': True
            }), 200
            
        except openai.OpenAIError as e:
            logging.error(f"OpenAI API error: {str(e)}")
            return jsonify({
                'error': 'Failed to generate title using AI',
                'success': False
            }), 500
        except Exception as e:
            logging.error(f"Unexpected error during title generation: {str(e)}")
            return jsonify({
                'error': 'Internal error during title generation',
                'success': False
            }), 500
            
    except Exception as e:
        logging.error(f"Error in generate_title endpoint: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'success': False
        }), 500

# =============================================================================
# REST API ENDPOINTS
# =============================================================================

@app.route('/generate-blog', methods=['POST'])
@require_auth
@check_generation_limits()
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
    
    # Use task_id from frontend if provided, otherwise generate unique task identifier
    task_id = data.get('task_id', str(uuid.uuid4()))
    
    # Get authenticated user information
    user_id = g.user_id
    user_email = g.user_email
    user_role = g.user_role
    
    # Create task record for tracking with user information
    active_tasks[task_id] = {
        'id': task_id,
        'topic': topic,
        'status': 'queued',
        'created_at': datetime.now().isoformat(),
        'current_step': 'Queued for processing',
        'result': None,
        'error': None,
        'user_id': user_id,
        'user_email': user_email,
        'user_role': user_role
    }
    
    # Start background blog generation in separate thread
    thread = threading.Thread(
        target=background_blog_generation,
        args=(task_id, topic)  # SSE version - no room_id needed
    )
    thread.daemon = True  # Thread will die when main program exits
    thread.start()
    
    # Return task information to frontend
    return jsonify({
        'task_id': task_id,
        'status': 'queued',
        'message': 'Blog generation started. Connect to SSE stream for real-time updates.'
    }), 202

@app.route('/stream/<task_id>', methods=['GET'])
def stream_task_updates(task_id):
    """
    Server-Sent Events (SSE) endpoint for real-time task updates.
    
    This endpoint provides a persistent HTTP connection that streams
    real-time updates for a specific blog generation task.
    
    Note: SSE authentication is handled via query parameter since EventSource
    doesn't support custom headers. The JWT token should be passed as ?token=<jwt_token>
    
    Args:
        task_id (str): The unique task identifier to stream updates for
        
    Returns:
        Server-Sent Events stream with updates in the format:
        data: {"status": "in_progress", "message": "Current step...", "progress": 0.5}
        
    Security:
        - Requires valid JWT token via query parameter
        - Users can only stream their own tasks (unless ADMIN)
        - Automatic connection cleanup on task completion/error
    """
    import time
    from auth_middleware import AuthMiddleware
    
    # Handle authentication via query parameter (since EventSource can't send headers)
    token = flask_request.args.get('token')
    if not token:
        return jsonify({'error': 'Authentication token required'}), 401
    
    try:
        auth_middleware = AuthMiddleware()
        user_data = auth_middleware.verify_jwt_token(token)
        
        # Set user context for this request
        g.user_id = user_data.get('sub')
        g.user_email = user_data.get('email')
        g.user_role = user_data.get('role', 'USER')
        
    except Exception as e:
        return jsonify({'error': 'Invalid authentication token'}), 401
    
    # Verify task exists and user has access
    if task_id not in active_tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = active_tasks[task_id]
    
    # Check if user owns this task (users can only see their own tasks, admins see all)
    if g.user_role != 'ADMIN' and task.get('user_id') != g.user_id:
        return jsonify({'error': 'Task not found'}), 404

    def generate_updates():
        """Generator function that yields SSE-formatted updates"""
        last_status = None
        last_step = None
        last_log_count = 0
        
        # Send initial connection confirmation
        yield f"data: {json.dumps({'type': 'connected', 'task_id': task_id, 'message': 'Connected to task stream'})}\n\n"
        
        while True:
            try:
                # Get current task status
                if task_id not in active_tasks:
                    # Task was removed (completed or failed)
                    yield f"data: {json.dumps({'type': 'stream_ended', 'message': 'Task stream ended'})}\n\n"
                    break
                
                current_task = active_tasks[task_id]
                current_status = current_task.get('status')
                current_step = current_task.get('current_step')
                
                # Check for new detailed logs
                detailed_logs = current_task.get('detailed_logs', [])
                current_log_count = len(detailed_logs)
                
                # Send new log entries
                if current_log_count > last_log_count:
                    for i in range(last_log_count, current_log_count):
                        log_entry = detailed_logs[i]
                        log_data = {
                            'type': 'log_update',
                            'task_id': task_id,
                            'timestamp': log_entry['timestamp'],
                            'step': log_entry['step'],
                            'message': log_entry['message'],
                            'progress': log_entry['progress']
                        }
                        yield f"data: {json.dumps(log_data)}\n\n"
                    
                    last_log_count = current_log_count
                
                # Send status update if status or step changed
                if current_status != last_status or current_step != last_step:
                    update_data = {
                        'type': 'status_update',
                        'task_id': task_id,
                        'status': current_status,
                        'current_step': current_step,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Add progress information for different statuses
                    if current_status == 'in_progress':
                        update_data['progress'] = 0.5
                    elif current_status == 'completed':
                        update_data['progress'] = 1.0
                        update_data['result'] = current_task.get('result')
                    elif current_status == 'failed':
                        update_data['progress'] = 0.0
                        update_data['error'] = current_task.get('error')
                    
                    yield f"data: {json.dumps(update_data)}\n\n"
                    
                    last_status = current_status
                    last_step = current_step
                    
                    # End stream if task is completed or failed
                    if current_status in ['completed', 'failed']:
                        logging.info(f"SSE stream ending for task {task_id} with status: {current_status}")
                        # Send final stream_ended message
                        yield f"data: {json.dumps({'type': 'stream_ended', 'task_id': task_id, 'message': 'Task completed'})}\n\n"
                        
                        # Schedule task cleanup after a short delay to allow final message delivery
                        def cleanup_task():
                            time.sleep(2)  # Give client time to process final message
                            if task_id in active_tasks:
                                logging.info(f"Cleaning up completed task: {task_id}")
                                del active_tasks[task_id]
                        
                        import threading
                        cleanup_thread = threading.Thread(target=cleanup_task)
                        cleanup_thread.daemon = True
                        cleanup_thread.start()
                        
                        break
                
                # Wait before next check (0.5 second polling for more responsive log streaming)
                time.sleep(0.5)
                
            except Exception as e:
                logging.error(f"SSE stream error for task {task_id}: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': 'Stream error occurred'})}\n\n"
                break
    
    # Return SSE response with proper headers
    response = Response(
        generate_updates(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control'
        }
    )
    return response

@app.route('/task-status/<task_id>', methods=['GET'])
@require_auth
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
    
    task = active_tasks[task_id]
    
    # Check if user owns this task (users can only see their own tasks, admins see all)
    if g.user_role != 'ADMIN' and task.get('user_id') != g.user_id:
        return jsonify({'error': 'Task not found'}), 404

    return jsonify(task), 200

@app.route('/tasks', methods=['GET'])
@require_auth
@require_role(['ADMIN'])
def get_all_tasks():
    """
    Get all tasks for debugging and monitoring purposes.
    
    This endpoint is primarily used for:
    - Development debugging
    - System monitoring
    - Administrative oversight
    
    ADMIN ONLY - Regular users should use /my-tasks
    
    Response:
        [
            {task_record_1},
            {task_record_2},
            ...
        ]
    """
    return jsonify(list(active_tasks.values())), 200


@app.route('/my-tasks', methods=['GET'])
@require_auth
def get_user_tasks():
    """
    Get all tasks for the authenticated user.
    
    Users can only see their own tasks.
    
    Response:
        [
            {task_record_1},
            {task_record_2},
            ...
        ]
    """
    user_tasks = [
        task for task in active_tasks.values()
        if task.get('user_id') == g.user_id
    ]
    return jsonify(user_tasks), 200


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
    emit('connected', {'message': 'Connected to blog generation service'})

@socketio.on('disconnect')
def handle_disconnect():
    """
    Handle WebSocket disconnections.
    
    This event fires when a frontend client closes their WebSocket connection.
    Used primarily for logging and cleanup if needed.
    """
    pass

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
    - HTTPS: Automatically enabled if certificates are found
    - debug=True: Enable development mode with auto-reload
    - host='0.0.0.0': Accept connections from any IP address
    - port=5000: Standard Flask development port
    
    Note: In production, this should be run through a proper WSGI server
    like Gunicorn with proper configuration for WebSocket support.
    """
    # Get server configuration (with HTTPS if available)
    server_config = get_server_config()
    
    # Log server startup information
    protocol = "HTTPS" if server_config.get('ssl_context') else "HTTP"
    logging.info(f"🚀 Starting {protocol} server on {server_config['host']}:{server_config['port']}")
    
    # Start the server with SocketIO
    socketio.run(app, **server_config)