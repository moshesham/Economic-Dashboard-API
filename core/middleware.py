"""
Middleware for request/response logging with correlation IDs.
"""

import logging
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from core.logging import set_correlation_id, get_correlation_id, clear_correlation_id

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses with correlation IDs.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler
            
        Returns:
            HTTP response
        """
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = set_correlation_id()
        else:
            set_correlation_id(correlation_id)
        
        # Log request
        start_time = time.time()
        logger.info(
            f"Request started",
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": dict(request.query_params),
                    "client_host": request.client.host if request.client else None,
                }
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": round(duration * 1000, 2),
                        "error": str(e),
                    }
                },
                exc_info=True
            )
            clear_correlation_id()
            raise
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        # Log response
        logger.info(
            f"Request completed",
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                }
            }
        )
        
        # Clear correlation ID from context
        clear_correlation_id()
        
        return response
