"""Logging configuration for AI Usage Analytics Dashboard."""

import logging
import json
import sys
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional
from google.cloud import logging as cloud_logging

from .config import config


class StructuredFormatter(logging.Formatter):
    """Enhanced JSON formatter for structured logging with comprehensive metadata."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Base log entry with essential fields
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "source_location": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName
            },
            "environment": config.env,
            "project_id": config.project_id,
            "service_name": "ai-usage-analytics",
            "service_version": "1.0.0"
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "stack_trace": self.formatException(record.exc_info)
            }

        # Add essential tracing fields
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
            log_entry["trace"] = f"projects/{config.project_id}/traces/{record.request_id}"

        if hasattr(record, "component"):
            log_entry["component"] = record.component

        if hasattr(record, "operation"):
            log_entry["operation"] = record.operation

        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id

        if hasattr(record, "platform"):
            log_entry["platform"] = record.platform

        # Add performance metrics if present
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms

        if hasattr(record, "record_count"):
            log_entry["record_count"] = record.record_count

        # Add HTTP context if present
        if hasattr(record, "http_method"):
            log_entry["http_request"] = {
                "method": record.http_method,
                "url": getattr(record, "http_url", None),
                "status": getattr(record, "http_status", None),
                "response_size": getattr(record, "http_response_size", None)
            }

        # Add error context if present
        if hasattr(record, "error_code"):
            log_entry["error"] = {
                "code": record.error_code,
                "type": getattr(record, "error_type", None),
                "category": getattr(record, "error_category", None)
            }

        # Add custom labels/metadata
        if hasattr(record, "labels"):
            log_entry["labels"] = record.labels

        # Add any extra fields passed via the 'extra' parameter
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "levelname", "levelno", "pathname",
                          "filename", "module", "lineno", "funcName", "created", "msecs",
                          "relativeCreated", "thread", "threadName", "processName", "process",
                          "exc_info", "exc_text", "stack_info", "getMessage"]:
                if key not in log_entry and not key.startswith("_"):
                    log_entry[key] = value

        return json.dumps(log_entry, default=str)


def setup_logging() -> logging.Logger:
    """Setup structured logging with Cloud Logging integration."""

    # Create logger
    logger = logging.getLogger("ai_usage_analytics")
    logger.setLevel(getattr(logging, config.log_level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler with structured formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter())
    logger.addHandler(console_handler)

    # Cloud Logging integration (if not in debug mode)
    if not config.debug:
        try:
            client = cloud_logging.Client()
            cloud_handler = client.get_default_handler()
            cloud_handler.setFormatter(StructuredFormatter())
            logger.addHandler(cloud_handler)
        except Exception as e:
            logger.warning(f"Could not setup Cloud Logging: {e}")

    return logger


def generate_request_id() -> str:
    """Generate a unique request ID for tracing."""
    return str(uuid.uuid4())


def get_logger(component: str = None, request_id: str = None) -> logging.Logger:
    """Get logger instance with optional component and request_id context."""
    logger = logging.getLogger("ai_usage_analytics")

    # Prepare extra context
    extra = {}
    if component:
        extra["component"] = component
    if request_id:
        extra["request_id"] = request_id

    if extra:
        # Create adapter to add context
        return logging.LoggerAdapter(logger, extra)

    return logger


class RequestContextLogger:
    """Logger with persistent request context for multi-step operations."""

    def __init__(self, component: str, request_id: str = None, operation: str = None):
        """Initialize with context that will be added to all log messages."""
        self.request_id = request_id or generate_request_id()
        self.component = component
        self.operation = operation
        self.start_time = time.time()

        # Base context for all logs
        self.context = {
            "request_id": self.request_id,
            "component": component
        }

        if operation:
            self.context["operation"] = operation

        self.logger = logging.LoggerAdapter(
            logging.getLogger("ai_usage_analytics"),
            self.context
        )

    def info(self, message: str, **kwargs):
        """Log info message with request context."""
        self.logger.info(message, extra=kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message with request context."""
        self.logger.debug(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with request context."""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, error: Exception = None, **kwargs):
        """Log error message with request context and optional exception."""
        if error:
            kwargs.update({
                "error_type": type(error).__name__,
                "error_message": str(error)
            })
        self.logger.error(message, extra=kwargs, exc_info=error is not None)

    def log_operation_start(self, operation: str, **metadata):
        """Log the start of an operation."""
        self.operation = operation
        self.context["operation"] = operation
        self.start_time = time.time()

        self.info(f"Starting operation: {operation}", **metadata)

    def log_operation_complete(self, operation: str = None, **metadata):
        """Log the completion of an operation with timing."""
        op_name = operation or self.operation or "operation"
        duration_ms = (time.time() - self.start_time) * 1000

        self.info(
            f"Completed operation: {op_name}",
            duration_ms=duration_ms,
            **metadata
        )

    def log_operation_error(self, operation: str = None, error: Exception = None, **metadata):
        """Log an operation error with timing."""
        op_name = operation or self.operation or "operation"
        duration_ms = (time.time() - self.start_time) * 1000

        self.error(
            f"Operation failed: {op_name}",
            error=error,
            duration_ms=duration_ms,
            **metadata
        )

    def log_api_call(self, platform: str, endpoint: str, response_time_ms: float,
                    record_count: int = None, status_code: int = None):
        """Log API call with performance metrics."""
        self.info(
            f"API call completed: {platform} {endpoint}",
            platform=platform,
            endpoint=endpoint,
            duration_ms=response_time_ms,
            record_count=record_count,
            http_status=status_code
        )

    def log_data_processing(self, stage: str, input_count: int, output_count: int,
                           processing_time_ms: float = None):
        """Log data processing stage with metrics."""
        extra = {
            "stage": stage,
            "input_count": input_count,
            "output_count": output_count
        }

        if processing_time_ms is not None:
            extra["duration_ms"] = processing_time_ms

        self.info(
            f"Data processing stage: {stage} ({input_count} → {output_count})",
            **extra
        )

    def log_bigquery_operation(self, table_name: str, operation: str, record_count: int,
                              duration_ms: float):
        """Log BigQuery operation with performance metrics."""
        self.info(
            f"BigQuery {operation}: {table_name}",
            table_name=table_name,
            operation=operation,
            record_count=record_count,
            duration_ms=duration_ms
        )