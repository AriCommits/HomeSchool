# src/homeschool/logging.py
"""
Logging configuration for the Homeschool project.
Configures structlog with appropriate processors and handlers.
"""

import logging
import logging.handlers
import sys
import re
from pathlib import Path
from typing import Any, Dict

import structlog
from structlog.types import Processor

# Security: Keys that should never be logged
SENSITIVE_KEYS = frozenset([
    'auth_token', 'token', 'password', 'secret', 'credential',
    'api_key', 'apikey', 'private_key', 'token', 'access_token',
    'chromadb.auth_token', 'CHROMA_TOKEN', 'api_token', 'session_token'
])

# Patterns that might contain sensitive data
SENSITIVE_PATTERNS = [
    r'[a-zA-Z0-9]{32,}',  # Long alphanumeric strings (likely tokens)
    r'-----BEGIN.*PRIVATE KEY-----',
    r'sk-[a-zA-Z0-9]{20,}',  # OpenAI-style keys
]


def _sanitize_log_data(event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove sensitive information from log events.
    Called as a processor before logs are written.
    """
    # Check log level - be more restrictive in DEBUG mode
    log_level = event_dict.get('level', 'INFO').upper()
    
    # Create a new dict with sanitized values
    sanitized = {}
    for key, value in event_dict.items():
        key_lower = key.lower()
        
        # Skip completely sensitive keys
        if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
            sanitized[key] = "[REDACTED]"
            continue
        
        # Sanitize string values
        if isinstance(value, str):
            # Check if string looks like a token
            if len(value) >= 32 and any(c.isalpha() for c in value) and any(c.isdigit() for c in value):
                # Might be a token - sanitize
                sanitized[key] = value[:4] + "[REDACTED]" + value[-4:] if len(value) > 16 else "[REDACTED]"
                continue
            sanitized[key] = value
        else:
            sanitized[key] = value
    
    return sanitized


def _filter_sensitive_fields(processor: Processor) -> Processor:
    """
    Wrap a processor to filter sensitive data from log output.
    """
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        result = processor(*args, **kwargs)
        if isinstance(result, dict):
            return _sanitize_log_data(result)
        return result
    return wrapped


def add_log_level(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add log level to the event dict.
    """
    event_dict["level"] = method_name.upper()
    return event_dict


def configure_logging(
    log_level: str = "INFO",
    log_file: Path | None = None,
    json_logs: bool = False,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> None:
    """
    Configure structlog for the application.
    
    Args:
        log_level: Minimum log level to output (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
        json_logs: Whether to output logs as JSON (True) or human-readable (False)
        max_bytes: Maximum size in bytes before rotating logs
        backup_count: Number of backup log files to keep
    """
    # Remove any existing handlers to avoid duplicate logs
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Configure standard library logging
    if log_file:
        # Use rotating file handler to prevent disk space issues
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logging.root.addHandler(handler)
    else:
        # Default to stdout
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, log_level.upper()),
        )

    # Shared processors for both JSON and console output
    # Security: Always sanitize sensitive data regardless of log level
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        _sanitize_log_data,  # Security: Remove sensitive data from all logs
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # Choose renderer based on output format
    if json_logs:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    # Configure structlog
    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Get a configured structlog logger.
    
    Args:
        name: Optional logger name (will be added to context)
        
    Returns:
        Configured structlog BoundLogger
    """
    logger = structlog.get_logger()
    if name:
        logger = logger.bind(logger_name=name)
    return logger