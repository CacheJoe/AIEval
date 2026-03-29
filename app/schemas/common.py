"""Shared API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MessageResponse(BaseModel):
    """Simple message payload."""

    message: str


class HealthResponse(BaseModel):
    """Health check payload."""

    status: str
    timestamp: datetime

