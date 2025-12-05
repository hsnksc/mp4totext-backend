# Dockerfile for MP4toText Backend
# Python 3.12 + FastAPI + Celery Worker (Production Ready)
# Build: 2025-12-05-v2

FROM python:3.12-slim AS base

# Force cache bust for Coolify runc issue
ARG CACHEBUST=2

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_HOME=/app

# Set build arguments
ARG DEBIAN_FRONTEND=noninteractive

# Ensure shell is available (fix for runc issues)
SHELL ["/bin/bash", "-c"]

# Install system dependencies + supervisor + create directories
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    build-essential \
    gcc \
    libpq-dev \
    libffi-dev \
    ffmpeg \
    curl \
    ca-certificates \
    supervisor \
    libsndfile1 \
    libsndfile1-dev \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /app/logs /app/uploads /app/storage

# Set working directory
WORKDIR $APP_HOME

# Copy requirements first (for better caching)
COPY requirements.txt .

# Upgrade pip and install dependencies in stages to avoid memory issues
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install core dependencies first
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    celery==5.5.3 \
    redis==5.0.1 \
    sqlalchemy==2.0.23 \
    pydantic==2.5.0 \
    pydantic-settings==2.1.0

# Install PyTorch CPU and Whisper with pre-built wheels (avoid source build timeout)
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.5.1+cpu \
    torchaudio==2.5.1+cpu \
    triton==3.1.0 \
    && pip install --no-cache-dir openai-whisper==20240930

# Install remaining dependencies (skip already installed packages)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Fix Windows line endings (CRLF -> LF) and make startup script executable
RUN sed -i 's/\r$//' startup.sh && chmod +x startup.sh

# Copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start with startup script (runs migrations then supervisor)
CMD ["./startup.sh"]
