# Economic Dashboard API - Docker Image
# Multi-stage build for optimized production images
#
# Targets:
#   api        - slim image for the FastAPI service (~no ML packages)
#   production - full image for the worker/dashboard (all packages)

# ============================================================================
# Stage 1a: Build API-only virtualenv (fast - all API deps have binary wheels)
# ============================================================================
FROM python:3.11-slim AS builder-api

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VENV_PATH=/opt/venv

# No build-essential needed - all API dependencies have pre-built wheels
WORKDIR /app

COPY requirements-api.txt .
RUN python -m venv ${VENV_PATH} \
    && ${VENV_PATH}/bin/pip install --upgrade pip setuptools wheel \
    && ${VENV_PATH}/bin/pip install --prefer-binary -r requirements-api.txt

# ============================================================================
# Stage 1b: Build full virtualenv (API + worker/ML packages)
# ============================================================================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VENV_PATH=/opt/venv

# ML packages (xgboost, lightgbm, shap) may need compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the pre-built API venv and layer ML packages on top
COPY --from=builder-api ${VENV_PATH} ${VENV_PATH}

COPY requirements-worker.txt .
RUN ${VENV_PATH}/bin/pip install --prefer-binary -r requirements-worker.txt

# ============================================================================
# Stage 1c: Build dashboard virtualenv (API + dashboard-only packages)
# ============================================================================
FROM python:3.11-slim AS builder-dashboard

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VENV_PATH=/opt/venv

WORKDIR /app

# Start from API venv and add only dashboard visualization deps.
COPY --from=builder-api ${VENV_PATH} ${VENV_PATH}

COPY requirements-dashboard.txt .
RUN ${VENV_PATH}/bin/pip install --prefer-binary -r requirements-dashboard.txt

# ============================================================================
# Stage 2a: Slim API runtime image (no compiler toolchain, no ML wheels)
# ============================================================================
FROM python:3.11-slim AS api

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VENV_PATH=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

COPY --from=builder-api ${VENV_PATH} ${VENV_PATH}

COPY --chown=appuser:appgroup . .

RUN mkdir -p /app/data/duckdb/temp \
    /app/data/duckdb/snapshots \
    /app/data/duckdb/archives \
    /app/data/cache \
    /app/data/backups \
    /app/logs \
    && chown -R appuser:appgroup /app/data /app/logs

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)"

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================================================
# Stage 2b: Full production runtime image (worker + dashboard)
# ============================================================================
FROM python:3.11-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VENV_PATH=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Runtime libs for scientific wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

COPY --from=builder ${VENV_PATH} ${VENV_PATH}

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
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)"

# Default command (overridden by docker-compose)
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================================================
# Stage 2c: Dashboard runtime image (no ML training stack)
# ============================================================================
FROM python:3.11-slim AS dashboard

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VENV_PATH=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

COPY --from=builder-dashboard ${VENV_PATH} ${VENV_PATH}
COPY --chown=appuser:appgroup . .

RUN mkdir -p /app/data/duckdb/temp \
    /app/data/duckdb/snapshots \
    /app/data/duckdb/archives \
    /app/data/cache \
    /app/data/backups \
    /app/logs \
    && chown -R appuser:appgroup /app/data /app/logs

USER appuser

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]