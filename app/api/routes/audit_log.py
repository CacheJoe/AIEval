"""Audit log routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DBSession
from app.models.enums import AuditAction, UserRole
from app.schemas.audit import AuditLogRead
from app.services.audit_query_service import AuditQueryService
from app.services.audit_service import AuditService
from app.utils.exceptions import AppException

router = APIRouter(tags=["Audit"])


@router.get("/audit-log", response_model=list[AuditLogRead], status_code=status.HTTP_200_OK)
def list_audit_logs(
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(default=200, ge=1, le=500),
    action: str | None = Query(default=None),
) -> list[AuditLogRead]:
    """View recent audit logs."""
    if current_user.role != UserRole.ADMIN:
        raise AppException(status_code=403, message="Only ADMIN can view audit logs.")

    logs = AuditQueryService.list_logs(db, limit=limit, action=action)
    AuditService.record(
        db=db,
        action=AuditAction.AUDIT_VIEW,
        user_id=current_user.id,
        entity_type="audit_log",
        entity_id=None,
        details={"limit": limit, "action": action},
    )
    db.commit()
    return logs
