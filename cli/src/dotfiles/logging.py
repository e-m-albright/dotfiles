"""structlog configuration. Configured once at CLI entry; quiet by default."""

import logging

import structlog

from dotfiles.settings import LogLevel


def configure_logging(level: LogLevel = "WARNING") -> None:
    structlog.reset_defaults()
    numeric = getattr(logging, level.upper(), logging.WARNING)
    logging.basicConfig(format="%(message)s", level=numeric)
    logging.getLogger().setLevel(numeric)
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(numeric),
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.KeyValueRenderer(key_order=["event", "level"]),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
