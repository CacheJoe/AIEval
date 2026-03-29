"""Audit schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AuditAction


class AuditLogRead(BaseModel):
    """Audit log item."""

    id: str
    user_id: str | None
    user_email: str | None
    action: AuditAction
    entity_type: str | None
    entity_id: str | None
    details: dict | None
    timestamp: datetime

