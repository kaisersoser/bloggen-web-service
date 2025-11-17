#!/bin/bash
# Test database connection using current environment configuration
# This script loads .env file and runs the Python test script

set -e  # Exit on error

echo "🔧 Database Connection Test Script"
echo "=================================="
echo ""

# Navigate to backend directory
cd "$(dirname "$0")"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found in backend/"
    echo ""
    echo "Please create a .env file with your DATABASE_URL"
    echo "Or set DATABASE_URL environment variable manually"
    echo ""
    echo "Example:"
    echo '  export DATABASE_URL="postgresql://user:pass@host:port/db"'
    echo "  ./test_db_connection.sh"
    exit 1
fi

# Load environment variables from .env
echo "📄 Loading environment from .env file..."
set -a  # Auto-export all variables
source .env
set +a
echo ""

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL not found in .env file"
    exit 1
fi

echo "✅ DATABASE_URL loaded from .env (credentials hidden)"
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "🐍 Activating virtual environment..."
    source .venv/bin/activate
    echo ""
fi

# Run the Python test script
echo "🚀 Running connection test..."
echo ""
python test_db_connection.py

# Capture exit code
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Test completed successfully!"
else
    echo "❌ Test failed with exit code: $EXIT_CODE"
fi

exit $EXIT_CODE
