#!/bin/bash

# Immediate HTTP Mode Fix
# Temporarily disable HTTPS to get application working

echo "🚀 Switching to HTTP Mode - Immediate Fix"
echo "========================================"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Update backend environment to use HTTP
echo "📋 Configuring backend for HTTP..."
if [ -f "$PROJECT_ROOT/backend/.env" ]; then
    # Backup current .env
    cp "$PROJECT_ROOT/backend/.env" "$PROJECT_ROOT/backend/.env.https.backup"
    
    # Update HTTPS settings
    sed -i 's/FORCE_HTTPS="true"/FORCE_HTTPS="false"/g' "$PROJECT_ROOT/backend/.env"
    sed -i 's|API_URL="https://localhost:5000"|API_URL="http://localhost:5000"|g' "$PROJECT_ROOT/backend/.env"
    sed -i 's|FRONTEND_URL="https://localhost:3001"|FRONTEND_URL="http://localhost:3001"|g' "$PROJECT_ROOT/backend/.env"
    sed -i 's|NEXTAUTH_URL="https://localhost:3001"|NEXTAUTH_URL="http://localhost:3001"|g' "$PROJECT_ROOT/backend/.env"
    
    echo "✅ Backend configured for HTTP"
else
    echo "❌ Backend .env file not found"
fi

# Update frontend environment to use HTTP
echo "📋 Configuring frontend for HTTP..."
if [ -f "$PROJECT_ROOT/frontend-nextjs/blog-generator-ui/.env.local" ]; then
    # Backup current .env.local
    cp "$PROJECT_ROOT/frontend-nextjs/blog-generator-ui/.env.local" "$PROJECT_ROOT/frontend-nextjs/blog-generator-ui/.env.local.https.backup"
    
    # Update protocol mode
    sed -i 's/NEXT_PUBLIC_PROTOCOL_MODE=https/NEXT_PUBLIC_PROTOCOL_MODE=http/g' "$PROJECT_ROOT/frontend-nextjs/blog-generator-ui/.env.local"
    
    echo "✅ Frontend configured for HTTP"
else
    echo "❌ Frontend .env.local file not found"
fi

# Create HTTP development scripts
echo "📋 Creating HTTP development scripts..."

# Backend HTTP script
cat > "$PROJECT_ROOT/start-backend-http.sh" << 'EOF'
#!/bin/bash
cd backend
source .venv/bin/activate
echo "🚀 Starting backend in HTTP mode on http://localhost:5000"
python src/main.py
EOF

# Frontend HTTP script
cat > "$PROJECT_ROOT/start-frontend-http.sh" << 'EOF'
#!/bin/bash
cd frontend-nextjs/blog-generator-ui
echo "🚀 Starting frontend in HTTP mode on http://localhost:3001"
npm run dev:http
EOF

# Combined start script
cat > "$PROJECT_ROOT/start-http.sh" << 'EOF'
#!/bin/bash

echo "🚀 Starting Blog Generator in HTTP Mode"
echo "======================================"

# Function to kill background processes on exit
cleanup() {
    echo "🛑 Stopping services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}
trap cleanup INT

# Start backend
echo "📋 Starting backend (HTTP)..."
cd backend
source .venv/bin/activate
python src/main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend  
echo "📋 Starting frontend (HTTP)..."
cd frontend-nextjs/blog-generator-ui
npm run dev:http &
FRONTEND_PID=$!
cd ../..

echo ""
echo "🎉 Services started successfully!"
echo "================================"
echo "🔗 Backend:  http://localhost:5000"
echo "🔗 Frontend: http://localhost:3001"
echo ""
echo "✅ No SSL certificate issues in HTTP mode"
echo "🌐 Visit: http://localhost:3001"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
wait
EOF

chmod +x "$PROJECT_ROOT/start-backend-http.sh"
chmod +x "$PROJECT_ROOT/start-frontend-http.sh" 
chmod +x "$PROJECT_ROOT/start-http.sh"

echo "✅ HTTP development scripts created"

echo ""
echo "🎉 HTTP MODE CONFIGURATION COMPLETE!"
echo "==================================="
echo ""
echo "📋 Start Options:"
echo "  Quick Start: ./start-http.sh"
echo "  Manual:"
echo "    Backend:  ./start-backend-http.sh"
echo "    Frontend: ./start-frontend-http.sh"
echo ""
echo "🌐 Access Application:"
echo "  URL: http://localhost:3001"
echo "  ✅ No certificate errors"
echo "  ✅ No browser warnings"
echo ""
echo "📋 To revert to HTTPS later:"
echo "  - Restore .env files from .https.backup files"
echo "  - Fix SSL certificate issues"
echo "  - Change NEXT_PUBLIC_PROTOCOL_MODE back to https"
