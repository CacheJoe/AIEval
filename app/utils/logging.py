"""Logging configuration."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.utils.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure console and file logging once per process."""
    root_logger = logging.getLogger()
    if getattr(root_logger, "_aiales_configured", False):
        return

    settings.ensure_directories()
    log_file = settings.logs_dir / "app.log"
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    setattr(root_logger, "_aiales_configured", True)

