# Backend Dockerfile for Production Deployment
# Optimized for Railway deployment
# Updated: 2025-10-18 - Added startup diagnostics

FROM python:3.11-slim

# Cache-busting argument
ARG CACHEBUST=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cache-busting layer - forces rebuild from here down
RUN echo "Build timestamp: 2025-10-18-17:50:00"

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY start.sh ./start.sh

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Make startup script executable AFTER setting ownership
RUN chmod +x ./start.sh

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# Railway will provide PORT via environment variable
# No need to hardcode it here

# Start application directly with Python, PYTHONPATH already set
CMD ["python", "src/main.py"]
