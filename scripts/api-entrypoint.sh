#!/bin/bash
# API entrypoint script

set -e

echo "Starting Economic Dashboard API..."

# Wait for Redis if configured
if [ -n "$REDIS_HOST" ]; then
    echo "Waiting for Redis at $REDIS_HOST:${REDIS_PORT:-6379}..."
    for i in $(seq 1 30); do
        if nc -z "$REDIS_HOST" "${REDIS_PORT:-6379}" 2>/dev/null; then
            echo "Redis is ready!"
            break
        fi
        echo "Waiting for Redis... ($i/30)"
        sleep 1
    done
fi

# Run database migrations if needed
if [ -f "scripts/migrate.py" ]; then
    echo "Running database migrations..."
    python scripts/migrate.py
fi

# Start the API server
echo "Starting uvicorn server..."
exec uvicorn api.main:app \
    --host "${API_HOST:-0.0.0.0}" \
    --port "${API_PORT:-8000}" \
    --workers "${API_WORKERS:-1}" \
    --log-level "${LOG_LEVEL:-info}"
