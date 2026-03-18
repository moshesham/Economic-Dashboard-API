"""
Logging configuration module.

Sets up structured logging for the application with correlation IDs.
"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Optional
from datetime import datetime

from core.config import settings


# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class StructuredFormatter(logging.Formatter):
    """
    Structured JSON formatter for logs with correlation IDs.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


class ContextFilter(logging.Filter):
    """Add correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get() or "N/A"
        return True


def setup_logging(level: Optional[str] = None, structured: bool = None) -> None:
    """
    Configure application logging.
    
    Args:
        level: Optional log level override
        structured: Use structured JSON logging (default: True in production)
    """
    log_level = level or settings.LOG_LEVEL
    
    # Determine if structured logging should be used
    if structured is None:
        structured = settings.ENVIRONMENT == "production"
    
    # Configure handlers
    handler = logging.StreamHandler(sys.stdout)
    
    if structured:
        # Use JSON structured logging
        handler.setFormatter(StructuredFormatter())
    else:
        # Use human-readable logging
        log_format = "%(asctime)s - %(correlation_id)s - %(name)s - %(levelname)s - %(message)s"
        handler.setFormatter(logging.Formatter(log_format))
        handler.addFilter(ContextFilter())
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=[handler],
        force=True
    )
    
    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("yfinance").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured at level: {log_level}, structured: {structured}")


def get_logger(name: str) -> logging.Logger:
    """Get a named logger instance."""
    return logging.getLogger(name)


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set correlation ID for current context.
    
    Args:
        correlation_id: Correlation ID to set (generates UUID if not provided)
        
    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    return correlation_id_var.get()


def clear_correlation_id() -> None:
    """Clear correlation ID from current context."""
    correlation_id_var.set(None)
