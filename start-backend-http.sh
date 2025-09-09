#!/bin/bash
cd backend
source .venv/bin/activate
echo "🚀 Starting backend in HTTP mode on http://localhost:5000"
python src/main.py
