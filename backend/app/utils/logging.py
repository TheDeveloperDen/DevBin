"""Logging configuration utilities."""

import logging
import sys
from typing import Literal


def configure_logging(
    level: str = "INFO",
    log_format: Literal["text", "json"] = "text",
) -> None:
    """
    Configure application logging with specified format.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format - 'text' for human-readable, 'json' for structured
    """
    # Convert string level to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    if log_format == "json":
        try:
            import structlog

            # Configure structlog for JSON output
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer(),
                ],
                wrapper_class=structlog.stdlib.BoundLogger,
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                cache_logger_on_first_use=True,
            )

            # Configure standard logging to use structlog
            logging.basicConfig(
                format="%(message)s",
                stream=sys.stdout,
                level=numeric_level,
            )

            # Wrap standard library loggers with structlog
            structlog.stdlib.recreate_defaults(log_level=numeric_level)

        except ImportError:
            # Fallback to text format if structlog not installed
            logging.warning(
                "structlog not installed, falling back to text format. "
                "Install with: pip install structlog"
            )
            _configure_text_logging(numeric_level)
    else:
        _configure_text_logging(numeric_level)


def _configure_text_logging(level: int) -> None:
    """Configure standard text-based logging."""
    # Custom format with timestamp, level, name, and message
    log_format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logging.basicConfig(
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        level=level,
    )

    # Reduce noise from some verbose libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
