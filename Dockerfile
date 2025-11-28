# Economic Dashboard API - Docker Image
# Multi-stage build for optimized production image

# ============================================================================
# Stage 1: Base image with system dependencies
# ============================================================================
FROM python:3.11-slim AS base

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# ============================================================================
# Stage 2: Dependencies installation
# ============================================================================
FROM base AS dependencies

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Stage 3: Production image
# ============================================================================
FROM dependencies AS production

# Copy application code
COPY --chown=appuser:appgroup . .

# Create data directories
RUN mkdir -p /app/data/duckdb/temp \
    /app/data/duckdb/snapshots \
    /app/data/duckdb/archives \
    /app/data/cache \
    /app/data/backups \
    /app/logs \
    && chown -R appuser:appgroup /app/data /app/logs

# Switch to non-root user
USER appuser

# Expose ports
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (overridden by docker-compose)
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]