#!/bin/bash

# Blog Generator Setup Script
echo "🚀 Setting up AI Blog Generator..."

# Backend setup
echo "📦 Setting up backend..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install backend dependencies
echo "Installing backend dependencies..."
pip install Flask Flask-SocketIO Flask-CORS crewai crewai-tools python-dotenv

# Frontend setup
echo "🎨 Setting up frontend..."
cd ../frontend-nextjs/blog-generator-ui

# Install frontend dependencies
echo "Installing frontend dependencies..."
npm install

# Add socket.io-client if not already added
npm install socket.io-client

echo "✅ Setup complete!"
echo ""
echo "🔧 To run the application:"
echo "1. Backend: cd backend && source venv/bin/activate && python src/main.py"
echo "2. Frontend: cd frontend-nextjs/blog-generator-ui && npm run dev"
echo ""
echo "🌐 Access the application at: http://localhost:3000"
echo "🔌 WebSocket server will be running at: http://localhost:5000"
