"""Audit query helpers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogRead


class AuditQueryService:
    """Read audit logs for dashboards and compliance reviews."""

    @staticmethod
    def list_logs(db: Session, limit: int = 200, action: str | None = None) -> list[AuditLogRead]:
        """Return recent audit log entries."""
        stmt = (
            select(AuditLog, User.email)
            .join(User, AuditLog.user_id == User.id, isouter=True)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        )
        if action:
            stmt = stmt.where(AuditLog.action == action)

        rows = db.execute(stmt).all()
        return [
            AuditLogRead(
                id=audit_log.id,
                user_id=audit_log.user_id,
                user_email=user_email,
                action=audit_log.action,
                entity_type=audit_log.entity_type,
                entity_id=audit_log.entity_id,
                details=audit_log.details,
                timestamp=audit_log.timestamp,
            )
            for audit_log, user_email in rows
        ]

