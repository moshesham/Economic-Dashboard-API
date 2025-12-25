# Production Features - Quick Start Guide

This guide helps you quickly set up and use the production features.

## Prerequisites

- Docker and Docker Compose installed
- Redis running (included in docker-compose.yml)

## Quick Setup

### 1. Update Environment Variables

Edit your `.env` file:

```env
# Enable production features
ENVIRONMENT=production

# Redis configuration for caching
REDIS_URL=redis://redis:6379/0
REDIS_CACHE_TTL=3600

# Logging configuration
LOG_LEVEL=INFO
```

### 2. Start Services

```bash
docker-compose up -d
```

### 3. Verify Setup

```bash
# Check health with cache status
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "components": {
#     "database": "healthy",
#     "redis": "healthy",
#     "cache": "healthy"
#   }
# }
```

## Using the Features

### API Response Caching

Cache is automatically enabled for GET requests. Check cache headers:

```bash
# First request (cache MISS)
curl -v http://localhost:8000/v1/data/fred?series=GDP 2>&1 | grep X-Cache
# X-Cache: MISS

# Second request (cache HIT)
curl -v http://localhost:8000/v1/data/fred?series=GDP 2>&1 | grep X-Cache
# X-Cache: HIT
```

Monitor cache performance:

```bash
curl http://localhost:8000/cache/stats
```

### Request Tracing with Correlation IDs

Every request gets a unique correlation ID for tracing:

```bash
# Request with correlation ID in response
curl -v http://localhost:8000/v1/data/fred?series=GDP 2>&1 | grep X-Correlation-ID

# Provide your own correlation ID
curl -H "X-Correlation-ID: my-trace-123" http://localhost:8000/v1/data/fred?series=GDP
```

View logs with correlation ID:

```bash
docker-compose logs api | grep "my-trace-123"
```

### Structured Logging

In production mode, logs are output as JSON:

```bash
# View JSON logs
docker-compose logs api --tail=10

# Parse logs with jq
docker-compose logs api --tail=100 | grep -o '{.*}' | jq '.'
```

Example log entry:

```json
{
  "timestamp": "2025-12-24T17:00:00.000Z",
  "level": "INFO",
  "logger": "api.main",
  "message": "Request completed",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "method": "GET",
  "path": "/v1/data/fred",
  "status_code": 200,
  "duration_ms": 45.23
}
```

## Cache Management

### Invalidate Cache

You can invalidate cache entries programmatically:

```python
from core.cache import invalidate_cache

# Invalidate specific pattern
invalidate_cache("http_cache:/v1/data/*")

# Invalidate all HTTP cache
invalidate_cache("http_cache:*")
```

### Cache Decorator for Custom Functions

```python
from core.cache import cached

@cached(ttl=300, key_prefix="custom")
async def expensive_calculation(param1: str, param2: int):
    # This will be cached for 5 minutes
    result = perform_expensive_operation(param1, param2)
    return result
```

## Monitoring

### Health Checks

The API provides multiple health check endpoints:

```bash
# Overall health
curl http://localhost:8000/health

# Readiness check (for load balancers)
curl http://localhost:8000/ready

# Cache statistics
curl http://localhost:8000/cache/stats
```

### Performance Metrics

View request performance in logs:

```bash
# Filter for slow requests (> 1000ms)
docker-compose logs api | grep -o '{.*}' | jq 'select(.duration_ms > 1000)'
```

## Troubleshooting

### Cache Not Working

**Symptom**: Always seeing `X-Cache: MISS`

**Solutions**:

1. Check Redis is running:
   ```bash
   docker-compose ps redis
   ```

2. Check Redis connection:
   ```bash
   curl http://localhost:8000/health | jq .components.redis
   ```

3. Verify cache stats:
   ```bash
   curl http://localhost:8000/cache/stats
   ```

### Logs Not in JSON Format

**Symptom**: Logs are human-readable instead of JSON

**Solution**: Ensure `ENVIRONMENT=production` in your `.env` file

```bash
# Check environment
docker-compose exec api printenv ENVIRONMENT

# Should output: production
```

### High Memory Usage

**Symptom**: Redis using too much memory

**Solutions**:

1. Reduce cache TTL:
   ```env
   REDIS_CACHE_TTL=1800  # 30 minutes instead of 1 hour
   ```

2. Monitor cache size:
   ```bash
   curl http://localhost:8000/cache/stats | jq .used_memory_human
   ```

3. Clear cache if needed:
   ```python
   from core.cache import cache_manager
   cache_manager.clear()  # Use with caution!
   ```

## Best Practices

### 1. Cache Invalidation

Invalidate cache when data changes:

```python
from core.cache import invalidate_cache

@app.post("/v1/ingest/fred")
async def ingest_fred_data(data: FredData):
    # Save data
    save_to_database(data)
    
    # Invalidate related cache
    invalidate_cache(f"http_cache:/v1/data/fred*")
    
    return {"status": "success"}
```

### 2. Correlation ID Propagation

When making internal service calls, propagate correlation ID:

```python
from core.logging import get_correlation_id
import httpx

async def call_external_service():
    correlation_id = get_correlation_id()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.example.com/data",
            headers={"X-Correlation-ID": correlation_id}
        )
```

### 3. Structured Logging

Include relevant context in logs:

```python
from core.logging import get_logger

logger = get_logger(__name__)

def process_data(data_id: str):
    logger.info(
        "Processing data",
        extra={
            "extra_fields": {
                "data_id": data_id,
                "record_count": len(data),
            }
        }
    )
```

## CI/CD Integration

The CI pipeline automatically:

- Runs tests with coverage reporting
- Generates coverage reports
- Uploads coverage to Codecov (if configured)
- Runs security scans

View CI status:

```bash
# Latest workflow runs
gh run list --limit 5

# View specific run
gh run view <run-id>
```

## Production Deployment

### 1. Environment Configuration

Ensure production environment variables are set:

```env
ENVIRONMENT=production
LOG_LEVEL=WARNING
REDIS_URL=redis://redis-prod:6379/0
REDIS_CACHE_TTL=3600
```

### 2. Health Check Configuration

Configure your load balancer:

```yaml
# Example: Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

# Readiness probe
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

### 3. Log Aggregation

Send JSON logs to your logging service:

```bash
# Example: CloudWatch Logs
docker-compose logs -f api | aws logs put-log-events ...

# Example: Elasticsearch
docker-compose logs -f api | logstash -f logstash.conf
```

## Next Steps

- Read the full documentation in `docs/PRODUCTION_FEATURES.md`
- Review test examples in `tests/test_cache.py` and `tests/test_middleware.py`
- Configure monitoring dashboards for cache metrics
- Set up alerts for unhealthy components

## Support

For issues or questions:

- Check the troubleshooting section above
- Review GitHub Issues
- Consult `docs/PRODUCTION_FEATURES.md` for detailed documentation
