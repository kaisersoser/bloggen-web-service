#!/bin/bash

# Script to restart both frontend and backend servers with new certificates

echo "🔄 Restarting Blog Generator servers with new SSL certificates..."

# Function# Verify ports are if ss -tuln | grep -q ":3001 "; then
    echo "✅ Frontend port 3001 is listening"
else
    echo "⚠️  Frontend port 3001 not detected (may still be starting up)"
fi

echo ""
echo "📝 Server logs:"
echo "   Backend: /home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/backend.log"
echo "   Frontend: /home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/frontend-nextjs/blog-generator-ui/frontend.log"
echo ""
echo "🔒 New certificates include proper Subject Alternative Names for better browser compatibility"
echo "💡 You may still need to accept the certificate once in your browser"
echo "📖 To view logs in real-time:"
echo "   tail -f backend/backend.log"
echo "   tail -f frontend-nextjs/blog-generator-ui/frontend.log"

# Store PIDs for later reference
echo "Backend PID: $BACKEND_PID" > /tmp/bloggen_pids.txt
echo "Frontend PID: $FRONTEND_PID" >> /tmp/bloggen_pids.txtning
echo "🔍 Verifying server ports..."
if ss -tuln | grep -q ":5000 "; then
    echo "✅ Backend port 5000 is listening"
else
    echo "⚠️  Backend port 5000 not detected (may still be starting up)"
fi

if ss -tuln | grep -q ":3001 "; then
    echo "✅ Frontend port 3001 is listening"
else
    echo "⚠️  Frontend port 3001 not detected (may still be starting up)"
fiecho "📝 Server logs:"
echo "   Backend: /home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/backend.log"
echo "   Frontend: /home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/frontend-nextjs/blog-generator-ui/frontend.log"
echo ""
echo "🔒 New certificates include proper Subject Alternative Names for better browser compatibility"
echo "💡 You may still need to accept the certificate once in your browser"
echo "📖 To view logs in real-time:"
echo "   tail -f backend/backend.log"
echo "   tail -f frontend-nextjs/blog-generator-ui/frontend.log"processes and wait for them to stop
kill_and_wait() {
    local process_name="$1"
    local timeout=30
    local count=0
    
    echo "🛑 Stopping $process_name processes..."
    
    # Initial kill attempts
    pkill -f "$process_name" 2>/dev/null || true
    
    # Wait until all processes are actually killed
    while pgrep -f "$process_name" > /dev/null; do
        if [ $count -ge $timeout ]; then
            echo "⚠️  Timeout reached, force killing $process_name..."
            pkill -9 -f "$process_name" 2>/dev/null || true
            sleep 2
            break
        fi
        
        echo "   Waiting for $process_name to stop... ($count/$timeout)"
        sleep 1
        ((count++))
        
        # Try killing again every 5 seconds
        if [ $((count % 5)) -eq 0 ]; then
            pkill -f "$process_name" 2>/dev/null || true
        fi
    done
    
    if ! pgrep -f "$process_name" > /dev/null; then
        echo "✅ $process_name stopped successfully"
    else
        echo "❌ Failed to stop $process_name completely"
    fi
}

# Function to kill processes on specific ports
kill_port_and_wait() {
    local port="$1"
    local timeout=15
    local count=0
    
    echo "🛑 Freeing port $port..."
    
    while lsof -ti:$port > /dev/null 2>&1; do
        if [ $count -ge $timeout ]; then
            echo "⚠️  Force killing processes on port $port..."
            lsof -ti:$port | xargs kill -9 2>/dev/null || true
            sleep 2
            break
        fi
        
        echo "   Stopping processes on port $port... ($count/$timeout)"
        lsof -ti:$port | xargs kill 2>/dev/null || true
        sleep 1
        ((count++))
    done
    
    if ! lsof -ti:$port > /dev/null 2>&1; then
        echo "✅ Port $port is free"
    else
        echo "❌ Port $port still in use"
    fi
}

# Kill backend processes
kill_and_wait "python src/main.py"

# Kill frontend processes
kill_and_wait "dev-dynamic.js"
kill_and_wait "dev-https.js"
kill_and_wait "npm run dev"
kill_and_wait "next dev"

# Free up the ports
kill_port_and_wait 5000
kill_port_and_wait 3001

echo "✅ All existing servers stopped"

# Function to start a service and wait for it to be ready
start_and_wait() {
    local service_name="$1"
    local start_command="$2"
    local port="$3"
    local max_wait=60
    local count=0
    
    echo "🚀 Starting $service_name..."
    
    # Start the service in background
    eval "$start_command" &
    local pid=$!
    
    echo "$service_name started with PID: $pid"
    
    # Wait for the port to be listening
    while ! ss -tuln | grep -q ":$port "; do
        if [ $count -ge $max_wait ]; then
            echo "❌ $service_name failed to start within $max_wait seconds"
            kill $pid 2>/dev/null || true
            return 1
        fi
        
        # Check if process is still running
        if ! kill -0 $pid 2>/dev/null; then
            echo "❌ $service_name process died during startup"
            return 1
        fi
        
        echo "   Waiting for $service_name to be ready... ($count/$max_wait)"
        sleep 1
        ((count++))
    done
    
    echo "✅ $service_name is ready on port $port (PID: $pid)"
    
    # Store PID for later reference
    if [ "$service_name" = "Backend" ]; then
        BACKEND_PID=$pid
    elif [ "$service_name" = "Frontend" ]; then
        FRONTEND_PID=$pid
    fi
    
    return 0
}

echo "🚀 Starting backend server..."
cd /home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend

# Clear previous log file
> backend.log

if ! start_and_wait "Backend" "source .venv/bin/activate && python src/main.py >> backend.log 2>&1" "5000"; then
    echo "❌ Failed to start backend server"
    echo "📝 Check backend.log for details"
    exit 1
fi

echo "🌐 Starting frontend server..."
cd /home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/frontend-nextjs/blog-generator-ui

# Clear previous log file
> frontend.log

if ! start_and_wait "Frontend" "npm run dev >> frontend.log 2>&1" "3001"; then
    echo "❌ Failed to start frontend server"
    echo "📝 Check frontend.log for details"
    # Kill backend if frontend fails
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo "✅ Servers started with new SSL certificates!"
echo "📍 Frontend: https://localhost:3001"
echo "📍 Backend: https://localhost:5000"
echo ""

# Verify ports are actually listening
echo "� Verifying server ports..."
if netstat -tuln | grep -q ":5000 "; then
    echo "✅ Backend port 5000 is listening"
else
    echo "⚠️  Backend port 5000 not detected (may still be starting up)"
fi

if netstat -tuln | grep -q ":3001 "; then
    echo "✅ Frontend port 3001 is listening"
else
    echo "⚠️  Frontend port 3001 not detected (may still be starting up)"
fi

echo ""
echo "�🔒 New certificates include proper Subject Alternative Names for better browser compatibility"
echo "💡 You may still need to accept the certificate once in your browser"
echo "📝 Check the logs above for any startup errors"

# Store PIDs for later reference
echo "Backend PID: $BACKEND_PID" > /tmp/bloggen_pids.txt
echo "Frontend PID: $FRONTEND_PID" >> /tmp/bloggen_pids.txt
