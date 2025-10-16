#!/bin/bash
# Run Railway network diagnostics using DATABASE_URL from .env

cd "$(dirname "$0")"

if [ -f ".env" ]; then
    set -a
    source .env
    set +a
    echo "✅ Loaded DATABASE_URL from .env"
    echo ""
fi

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python diagnose_railway_network.py
