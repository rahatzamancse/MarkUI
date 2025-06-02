# Multi-stage build for MarkUI - Frontend + Backend in single container
FROM node:20-alpine AS frontend-builder

# Set working directory for frontend build
WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package.json frontend/pnpm-lock.yaml ./

# Install pnpm and dependencies
RUN npm install -g pnpm
RUN pnpm install --frozen-lockfile

# Copy frontend source
COPY frontend/ ./

# Build the frontend for production
RUN pnpm build

# Python backend stage
FROM python:3.13-slim AS backend-builder

# Install system dependencies for marker library and PDF processing
RUN apt-get update && apt-get install -y \
    build-essential \
    poppler-utils \
    tesseract-ocr \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgdal-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app/backend

# Copy backend files
COPY backend/pyproject.toml backend/poetry.lock* ./

# Install Poetry and dependencies
RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --only=main --no-interaction --no-ansi --no-root

# Copy backend source
COPY backend/ ./

# Production stage with nginx
FROM python:3.13-slim AS production

# Install system dependencies and nginx
RUN apt-get update && apt-get install -y \
    nginx \
    poppler-utils \
    tesseract-ocr \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy Python dependencies from backend builder
COPY --from=backend-builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy backend application
COPY --from=backend-builder /app/backend ./backend

# Copy built frontend
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Create nginx configuration
COPY <<EOF /etc/nginx/sites-available/default
server {
    listen 80;
    root /app/frontend/build;
    index index.html;
    
    # Proxy API requests to FastAPI backend (must come before frontend routes)
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Proxy docs to backend (must come before frontend routes)
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /openapi.json {
        proxy_pass http://127.0.0.1:8000/openapi.json;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Proxy static and output files to backend
    location /static/ {
        proxy_pass http://127.0.0.1:8000/static/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /output/ {
        proxy_pass http://127.0.0.1:8000/output/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Serve static frontend files (catch-all, must come last)
    location / {
        try_files \$uri \$uri/ /index.html;
    }
    
    # Handle large file uploads
    client_max_body_size 100M;
}
EOF

# Create startup script
COPY <<EOF /app/start.sh
#!/bin/bash
set -e

echo "Starting MarkUI..."

# Function to handle signals
cleanup() {
    echo "Shutting down..."
    kill -TERM \$backend_pid 2>/dev/null || true
    nginx -s quit 2>/dev/null || true
    exit 0
}

trap cleanup SIGTERM SIGINT

# Start nginx in background
echo "Starting nginx..."
nginx

# Wait for Redis to be ready
echo "Waiting for Redis..."
sleep 10

# Start backend in background
echo "Starting backend..."
cd /app/backend
python run.py &
backend_pid=\$!

# Wait for backend to finish
wait \$backend_pid
EOF

RUN chmod +x /app/start.sh

# Create required directories
RUN mkdir -p /app/backend/uploads /app/backend/outputs /app/backend/static

# Set permissions
RUN chown -R app:app /app/backend/uploads /app/backend/outputs /app/backend/static

# Expose port 80 for nginx
EXPOSE 80

# Set environment variables
ENV HOST=127.0.0.1
ENV PORT=8000
ENV DEBUG=false
ENV REDIS_URL=redis://10.0.0.10:6379
ENV TORCH_DEVICE=cuda

# Start the application
CMD ["/app/start.sh"] 