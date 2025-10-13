#!/bin/bash
#
# Run all Phase 3.1 Database Service and Connection Pool tests
#
# Usage:
#   cd backend
#   source .venv/bin/activate
#   ./run_pool_tests.sh

set -e

echo "=================================================="
echo "Phase 3.1 Database Service Test Suite"
echo "=================================================="
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Error: Virtual environment not activated"
    echo "Please run: source .venv/bin/activate"
    exit 1
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  Warning: DATABASE_URL not set"
    echo "Tests may be skipped without database connection"
    echo ""
fi

# Navigate to backend directory if needed
if [ ! -f "src/main.py" ]; then
    if [ -f "backend/src/main.py" ]; then
        cd backend
    else
        echo "❌ Error: Cannot find backend/src/main.py"
        exit 1
    fi
fi

echo "Running Test Suite 1: DatabaseService Unit Tests"
echo "--------------------------------------------------"
pytest src/tests/test_database_service_pool.py -v --tb=short
echo ""

echo "Running Test Suite 2: Connection Pool Performance Tests"
echo "--------------------------------------------------------"
pytest src/tests/test_connection_pool_performance.py -v -s --tb=short
echo ""

echo "=================================================="
echo "✅ All Phase 3.1 tests completed!"
echo "=================================================="
echo ""
echo "📊 Summary:"
echo "  - DatabaseService functionality verified"
echo "  - Connection pool consolidation validated"
echo "  - Performance improvements measured"
echo "  - 70% reduction goal assessed"
echo ""
