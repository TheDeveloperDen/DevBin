"""Logging configuration utilities."""

import logging
import re
import sys
from typing import Literal


class HealthcheckLogFilter(logging.Filter):
    """Filter to suppress access logs for healthcheck endpoints."""

    HEALTHCHECK_PATTERN = re.compile(r'"[A-Z]+\s+/(health|ready)(\?[^\s]*)?\s+HTTP/')

    def filter(self, record: logging.LogRecord) -> bool:
        """Return False to drop healthcheck logs, True to keep others."""
        message = record.getMessage()
        return not self.HEALTHCHECK_PATTERN.search(message)


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

    # Set root logger level explicitly to ensure all child loggers respect it
    logging.getLogger().setLevel(numeric_level)

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
                force=True,
            )

            # Wrap standard library loggers with structlog
            structlog.stdlib.recreate_defaults(log_level=numeric_level)

            # Configure uvicorn loggers for JSON format
            formatter = logging.Formatter("%(message)s")
            _configure_uvicorn_loggers(numeric_level, formatter)

        except ImportError:
            # Fallback to text format if structlog not installed
            logging.warning("structlog not installed, falling back to text format. Install with: pip install structlog")
            _configure_text_logging(numeric_level)
    else:
        _configure_text_logging(numeric_level)


def _configure_text_logging(level: int) -> None:
    """Configure standard text-based logging."""
    # Custom format with timestamp, level, name, and message
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        format=log_format,
        datefmt=date_format,
        stream=sys.stdout,
        level=level,
        force=True,
    )

    # Configure uvicorn loggers to use the same format
    formatter = logging.Formatter(log_format, datefmt=date_format)
    _configure_uvicorn_loggers(level, formatter)


def _configure_uvicorn_loggers(level: int, formatter: logging.Formatter) -> None:
    """Configure uvicorn loggers to use consistent formatting."""
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False

    # Add healthcheck filter to access logger
    logging.getLogger("uvicorn.access").addFilter(HealthcheckLogFilter())
