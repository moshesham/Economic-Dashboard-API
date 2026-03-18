# Production Features Documentation

This document describes the production-grade features implemented in the Economic Dashboard API.

## Table of Contents

- [API Response Caching](#api-response-caching)
- [Centralized Logging](#centralized-logging)
- [Request Tracking](#request-tracking)
- [Health Checks](#health-checks)
- [CI/CD Pipeline](#cicd-pipeline)

## API Response Caching

### Overview

The API implements Redis-based caching to improve response times and reduce database load. Caching is automatic for GET requests to data endpoints.

### Features

- **Automatic Response Caching**: GET requests to `/v1/data`, `/v1/features`, `/v1/predictions`, and `/v1/signals` are automatically cached
- **Configurable TTL**: Default cache TTL is 1 hour (configurable via `REDIS_CACHE_TTL` environment variable)
- **Cache Headers**: Responses include `X-Cache: HIT` or `X-Cache: MISS` headers
- **Cache Statistics**: Available at `/cache/stats` endpoint
- **Graceful Degradation**: API continues to work even if Redis is unavailable

### Configuration

```env
# Redis connection
REDIS_URL=redis://localhost:6379/0

# Cache TTL in seconds (default: 3600 = 1 hour)
REDIS_CACHE_TTL=3600
```

### Usage Examples

#### Using the Cache Decorator

```python
from core.cache import cached

@cached(ttl=300, key_prefix="data:fred")
async def get_fred_data(series_id: str):
    # This function's results will be cached for 5 minutes
    data = fetch_from_database(series_id)
    return data
```

#### Cache Invalidation

```python
from core.cache import invalidate_cache

# Invalidate specific pattern
invalidate_cache("data:fred:*")

# Invalidate all data caches
invalidate_cache("http_cache:*")
```

#### Monitoring Cache Performance

```bash
# Get cache statistics
curl http://localhost:8000/cache/stats
```

Response:
```json
{
  "enabled": true,
  "total_commands": 15420,
  "keyspace_hits": 12336,
  "keyspace_misses": 3084,
  "used_memory_human": "2.3M"
}
```

### Cache Key Strategy

Cache keys are generated using:
- Request path
- Query parameters
- MD5 hash for uniqueness

Example: `http_cache:/v1/data/fred:a3c4f5d9e8b2a1c0`

## Centralized Logging

### Overview

The application implements structured logging with correlation IDs for request tracing across distributed systems.

### Features

- **Structured JSON Logging**: All logs in production use JSON format
- **Correlation IDs**: Every request gets a unique correlation ID for tracing
- **Request/Response Logging**: Automatic logging of all HTTP requests
- **Performance Metrics**: Request duration tracking
- **Log Levels**: Configurable log levels per environment

### Configuration

```env
# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Environment (affects log format)
ENVIRONMENT=production  # Uses JSON logging
# ENVIRONMENT=development  # Uses human-readable logging
```

### Log Format

#### Production (JSON):
```json
{
  "timestamp": "2025-12-24T16:30:00.000Z",
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

#### Development (Human-Readable):
```
2025-12-24 16:30:00,000 - a1b2c3d4-e5f6-7890 - api.main - INFO - Request completed
```

### Usage Examples

#### Using Correlation IDs in Code

```python
from core.logging import get_logger, get_correlation_id

logger = get_logger(__name__)

def process_request():
    correlation_id = get_correlation_id()
    logger.info(f"Processing request {correlation_id}")
```

#### Tracing Requests

All requests include correlation IDs in:
1. Response headers: `X-Correlation-ID`
2. All log entries related to that request

To trace a specific request:
```bash
# Send request and capture correlation ID
curl -v http://localhost:8000/v1/data/fred?series=GDP 2>&1 | grep X-Correlation-ID

# Search logs for that correlation ID
docker-compose logs api | grep "correlation-id-here"
```

### Log Aggregation

For production deployments, logs can be sent to:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **CloudWatch Logs** (AWS)
- **Google Cloud Logging** (GCP)
- **Azure Monitor** (Azure)

The structured JSON format makes it easy to index and query logs.

## Request Tracking

### Correlation IDs

Every HTTP request automatically receives a correlation ID that:
- Persists across all log entries for that request
- Is included in the response headers
- Can be provided by the client for distributed tracing

### Providing Your Own Correlation ID

```bash
curl -H "X-Correlation-ID: my-custom-id-123" \
  http://localhost:8000/v1/data/fred?series=GDP
```

The API will use your provided ID instead of generating one.

## Health Checks

### Available Endpoints

#### `/health` - Overall Health Status
Returns the health of all system components:

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-24T16:30:00.000Z",
  "version": "2.0.0",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "cache": "healthy"
  },
  "environment": "production"
}
```

#### `/ready` - Readiness Check
For load balancer integration:

```bash
curl http://localhost:8000/ready
```

Response:
```json
{
  "ready": true,
  "timestamp": "2025-12-24T16:30:00.000Z"
}
```

#### `/cache/stats` - Cache Statistics
Detailed cache performance metrics:

```bash
curl http://localhost:8000/cache/stats
```

### Docker Health Checks

Add to `docker-compose.yml`:
```yaml
services:
  api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## CI/CD Pipeline

### Overview

The CI/CD pipeline automatically tests, builds, and validates code on every push and pull request.

### Workflow Jobs

1. **Lint** - Code quality checks with Ruff
2. **Test** - Unit tests with coverage reporting
3. **Type Check** - Static type checking with mypy
4. **Security** - Security scanning with Bandit

### Code Coverage

- Coverage reports are generated for every test run
- Target: **80% code coverage**
- Reports uploaded to Codecov (if configured)
- Summary included in GitHub Actions output

### Running Locally

```bash
# Run tests with coverage
pytest tests/ -v --cov=api --cov=modules --cov=services --cov=core \
  --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html
```

### CI Configuration

The pipeline runs on:
- Every push to `main` or `develop` branches
- Every pull request to `main` or `develop`

Required secrets:
- `CODECOV_TOKEN` (optional) - For coverage reporting

### Status Badges

Add to README.md:
```markdown
[![CI](https://github.com/moshesham/Economic-Dashboard-API/workflows/CI%20-%20Test%20%26%20Lint/badge.svg)](https://github.com/moshesham/Economic-Dashboard-API/actions)
[![codecov](https://codecov.io/gh/moshesham/Economic-Dashboard-API/branch/main/graph/badge.svg)](https://codecov.io/gh/moshesham/Economic-Dashboard-API)
```

## Best Practices

### Caching

1. **Cache Invalidation**: Invalidate caches when data is updated via POST/PUT/DELETE endpoints
2. **TTL Strategy**: Use shorter TTL for frequently changing data, longer for stable data
3. **Cache Keys**: Ensure cache keys include all relevant parameters
4. **Monitoring**: Regularly check cache hit rates to optimize strategy

### Logging

1. **Log Levels**: Use appropriate log levels (DEBUG/INFO/WARNING/ERROR/CRITICAL)
2. **Structured Data**: Include relevant context in log messages
3. **Correlation IDs**: Always include correlation ID for distributed tracing
4. **Performance**: Avoid logging large payloads in production
5. **Sensitive Data**: Never log API keys, passwords, or PII

### Monitoring

1. **Health Checks**: Configure load balancers to use `/health` endpoint
2. **Metrics**: Monitor cache hit rates, response times, and error rates
3. **Alerts**: Set up alerts for degraded health status
4. **Log Aggregation**: Use centralized logging for production

## Troubleshooting

### Cache Issues

**Problem**: Cache not working
```bash
# Check Redis connection
curl http://localhost:8000/health | jq .components.redis

# Check cache stats
curl http://localhost:8000/cache/stats
```

**Solution**: Verify Redis is running and accessible:
```bash
docker-compose ps redis
docker-compose logs redis
```

### Logging Issues

**Problem**: Logs not structured
```bash
# Verify environment setting
echo $ENVIRONMENT

# Should be "production" for JSON logging
```

**Solution**: Set environment variable:
```bash
export ENVIRONMENT=production
```

### Performance Issues

**Problem**: High response times
```bash
# Check cache hit rate
curl http://localhost:8000/cache/stats | jq '.keyspace_hits, .keyspace_misses'

# Review logs for slow requests
docker-compose logs api | grep "duration_ms"
```

**Solution**: 
1. Increase cache TTL for stable data
2. Add more cached endpoints
3. Scale Redis if needed

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Redis Documentation](https://redis.io/documentation)
- [Pytest Documentation](https://docs.pytest.org/)
- [Codecov Documentation](https://docs.codecov.com/)
