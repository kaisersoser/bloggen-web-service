#!/bin/bash
set -e

echo "=========================================="
echo "Starting BlogGen Backend Application"
echo "=========================================="
echo "Working directory: $(pwd)"
echo "Python version: $(python --version)"
echo "PORT environment variable: ${PORT:-not set}"
echo "PYTHONPATH: ${PYTHONPATH:-not set}"
echo ""
echo "Directory structure:"
ls -la /app/
echo ""
echo "Contents of /app/src/:"
ls -la /app/src/ 2>/dev/null || echo "/app/src/ not found"
echo ""
echo "Attempting to import main modules..."
cd /app
export PYTHONPATH=/app/src:$PYTHONPATH
python -c "import sys; print('Python path:', sys.path)" || echo "Failed to run Python"
python -c "from config.protocol_config import get_protocol_config; print('✓ Successfully imported protocol_config')" || echo "✗ Failed to import protocol_config"
python -c "from core.config import config; print('✓ Successfully imported core.config')" || echo "✗ Failed to import core.config"
echo ""
echo "=========================================="
echo "Starting Python application..."
echo "=========================================="

# Run the application
exec python src/main.py
