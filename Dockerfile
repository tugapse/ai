# Dockerfile for JARVIS AI Assistant
FROM python:3.11-slim

# Prevent interactive prompts during apt package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system build tools, audio, C/C++ libraries, SQLite, and essential utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    gcc \
    g++ \
    portaudio19-dev \
    libsndfile1 \
    ffmpeg \
    sqlite3 \
    libsqlite3-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    AI_ASSISTANT_DIRECTORY=/app \
    TQDM_DISABLE=1

# Establish working directory
WORKDIR /app

# Upgrade base Python tooling
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirement manifests first for layer caching
COPY requirements.txt pyproject.toml README.md ./

# Install Python package dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e .

# Copy application source code and scripts
COPY . /app

# Grant execution permissions to docker-entrypoint script
RUN chmod +x /app/docker-entrypoint.sh

# Expose default Neural Hub FastAPI server port
EXPOSE 9999

# ENTRYPOINT locks in the executable. Any 'command' passed from docker-compose 
# (like "--server") gets appended to this script as an argument.
ENTRYPOINT ["/app/docker-entrypoint.sh"]