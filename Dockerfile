# Stage 1: Build the React SPA frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend

# Install dependencies
COPY frontend/package*.json ./
RUN npm ci

# Copy code and build production assets
COPY frontend/ ./
RUN npm run build

# Stage 2: Build the FastAPI backend serving the compiled React frontend
FROM python:3.13-slim
WORKDIR /app

# Install curl for health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and packages
COPY pyproject.toml LICENSE README.md ./
COPY private_pageindex/ ./private_pageindex/

# Copy compiled frontend build from Stage 1
COPY --from=frontend-builder /app/frontend/dist/ ./frontend/dist/

# Install python dependencies and application package
RUN pip install --no-cache-dir .

# Expose backend port
EXPOSE 8000

# Set Docker-specific environments
ENV HOST=0.0.0.0
ENV PORT=8000
ENV DATA_DIR=/app/data
ENV DOCKER_ENV=true

# Create data directory
RUN mkdir -p /app/data

# Run application web server
CMD ["python", "-m", "private_pageindex.cli", "serve"]
