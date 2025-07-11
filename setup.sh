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

# Unsplash API Setup
echo ""
echo "🖼️  Setting up Unsplash API Integration (Optional)"
echo "=================================================="
echo ""
echo "Would you like to set up Unsplash API for automatic image integration?"
echo "This will add professional images to your generated blog posts."
echo ""
read -p "Set up Unsplash API? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd ../../  # Go back to project root
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        echo "📄 Creating .env file from template..."
        cp .env.example .env
    fi
    
    echo ""
    echo "🔗 To get your Unsplash API key:"
    echo "   1. Visit: https://unsplash.com/developers"
    echo "   2. Sign in or create an account"
    echo "   3. Create a new application"
    echo "   4. Copy your Access Key"
    echo ""
    
    read -p "Enter your Unsplash Access Key (or press Enter to skip): " access_key
    
    if [ ! -z "$access_key" ]; then
        # Update or add the access key to .env
        if grep -q "UNSPLASH_ACCESS_KEY" .env; then
            # Update existing key
            sed -i "s/UNSPLASH_ACCESS_KEY=.*/UNSPLASH_ACCESS_KEY=$access_key/" .env
            echo "✅ Updated UNSPLASH_ACCESS_KEY in .env"
        else
            # Add new key
            echo "UNSPLASH_ACCESS_KEY=$access_key" >> .env
            echo "✅ Added UNSPLASH_ACCESS_KEY to .env"
        fi
        
        echo ""
        echo "🧪 Testing Unsplash integration..."
        python test_unsplash.py
        echo ""
        echo "🎉 Unsplash integration setup complete!"
        echo "   Your blog posts will now include professional images automatically!"
    else
        echo "⏭️  Skipped Unsplash setup. You can run 'python test_unsplash.py' later to set this up."
    fi
else
    echo "⏭️  Skipped Unsplash setup. Images will use placeholder fallbacks."
fi
echo ""
echo "🔧 To run the application:"
echo "1. Backend: cd backend && source venv/bin/activate && python src/main.py"
echo "2. Frontend: cd frontend-nextjs/blog-generator-ui && npm run dev"
echo ""
echo "🌐 Access the application at: http://localhost:3000"
echo "🔌 WebSocket server will be running at: http://localhost:5000"
