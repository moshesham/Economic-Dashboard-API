"""
Tests for logging module with correlation IDs.
"""

import pytest
import logging
import json
from unittest.mock import patch, MagicMock
from core.logging import (
    StructuredFormatter,
    ContextFilter,
    setup_logging,
    get_logger,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
)


class TestCorrelationID:
    """Tests for correlation ID management."""
    
    def test_set_correlation_id(self):
        """Test setting a correlation ID."""
        test_id = "test-correlation-123"
        result = set_correlation_id(test_id)
        assert result == test_id
        assert get_correlation_id() == test_id
        clear_correlation_id()
    
    def test_auto_generate_correlation_id(self):
        """Test auto-generating a correlation ID."""
        result = set_correlation_id()
        assert result is not None
        assert len(result) > 0
        assert get_correlation_id() == result
        clear_correlation_id()
    
    def test_clear_correlation_id(self):
        """Test clearing correlation ID."""
        set_correlation_id("test-123")
        clear_correlation_id()
        assert get_correlation_id() is None


class TestStructuredFormatter:
    """Tests for StructuredFormatter class."""
    
    def test_structured_formatter_basic(self):
        """Test basic structured log formatting."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        set_correlation_id("test-123")
        result = formatter.format(record)
        clear_correlation_id()
        
        # Parse JSON output
        log_data = json.loads(result)
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test"
        assert log_data["message"] == "Test message"
        assert log_data["correlation_id"] == "test-123"
        assert "timestamp" in log_data
    
    def test_structured_formatter_with_exception(self):
        """Test structured formatting with exception info."""
        formatter = StructuredFormatter()
        
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg="Error occurred",
                args=(),
                exc_info=exc_info
            )
            
            result = formatter.format(record)
            log_data = json.loads(result)
            
            assert log_data["level"] == "ERROR"
            assert "exception" in log_data
            assert "ValueError" in log_data["exception"]


class TestContextFilter:
    """Tests for ContextFilter class."""
    
    def test_context_filter_adds_correlation_id(self):
        """Test context filter adds correlation ID to log record."""
        filter_obj = ContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None
        )
        
        set_correlation_id("filter-test-123")
        filter_obj.filter(record)
        
        assert hasattr(record, 'correlation_id')
        assert record.correlation_id == "filter-test-123"
        clear_correlation_id()
    
    def test_context_filter_no_correlation_id(self):
        """Test context filter when no correlation ID is set."""
        filter_obj = ContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None
        )
        
        clear_correlation_id()
        filter_obj.filter(record)
        
        assert hasattr(record, 'correlation_id')
        assert record.correlation_id == "N/A"


class TestSetupLogging:
    """Tests for setup_logging function."""
    
    @patch('core.logging.settings')
    def test_setup_logging_development(self, mock_settings):
        """Test logging setup in development mode."""
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.ENVIRONMENT = "development"
        
        setup_logging()
        
        # Verify logging is configured
        logger = get_logger("test")
        assert logger is not None
        assert logger.level <= logging.INFO
    
    @patch('core.logging.settings')
    def test_setup_logging_production(self, mock_settings):
        """Test logging setup in production mode."""
        mock_settings.LOG_LEVEL = "WARNING"
        mock_settings.ENVIRONMENT = "production"
        
        setup_logging()
        
        # Verify logging is configured
        logger = get_logger("test")
        assert logger is not None
    
    def test_get_logger(self):
        """Test getting a named logger."""
        logger = get_logger("test.module")
        assert logger is not None
        assert logger.name == "test.module"
