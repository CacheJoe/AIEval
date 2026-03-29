"""Audit service helpers."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditAction


class AuditService:
    """Centralized audit log writer."""

    @staticmethod
    def record(
        db: Session,
        action: AuditAction | str,
        user_id: str | None,
        details: dict[str, Any] | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> AuditLog:
        """Create an audit log entry without committing."""
        normalized_action = AuditAction(action) if isinstance(action, str) else action
        audit_log = AuditLog(
            user_id=user_id,
            action=normalized_action,
            details=details,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        db.add(audit_log)
        return audit_log

