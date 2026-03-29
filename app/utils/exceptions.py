"""Custom application exceptions."""

from __future__ import annotations

from typing import Any


class AppException(Exception):
    """Raised for expected domain/application failures."""

    def __init__(self, status_code: int, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.details = details

