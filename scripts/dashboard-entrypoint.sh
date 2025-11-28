#!/bin/bash
# Dashboard entrypoint script

set -e

echo "Starting Economic Dashboard (Streamlit)..."

# Wait for API to be healthy
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

# Start Streamlit
echo "Starting Streamlit server..."
exec streamlit run app.py \
    --server.address "${STREAMLIT_HOST:-0.0.0.0}" \
    --server.port "${STREAMLIT_PORT:-8501}" \
    --server.headless true \
    --browser.gatherUsageStats false \
    --theme.base dark
