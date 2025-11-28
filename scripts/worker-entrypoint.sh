#!/bin/bash
# Worker entrypoint script

set -e

echo "Starting Economic Dashboard Worker..."

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

# Wait for API to be healthy (optional)
if [ -n "$API_HOST" ] && [ -n "$API_PORT" ]; then
    echo "Waiting for API at $API_HOST:$API_PORT..."
    for i in $(seq 1 60); do
        if curl -s "http://$API_HOST:$API_PORT/health" > /dev/null 2>&1; then
            echo "API is ready!"
            break
        fi
        echo "Waiting for API... ($i/60)"
        sleep 1
    done
fi

# Start the worker
echo "Starting background worker..."
exec python worker.py
