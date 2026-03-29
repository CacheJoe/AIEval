"""Runtime settings routes."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBSession
from app.models.enums import AuditAction, UserRole
from app.schemas.settings import RuntimeSettingsRead
from app.services.audit_service import AuditService
from app.services.settings_service import SettingsService
from app.utils.exceptions import AppException

router = APIRouter(tags=["Settings"])


@router.get("/settings", response_model=RuntimeSettingsRead, status_code=status.HTTP_200_OK)
def get_runtime_settings(db: DBSession, current_user: CurrentUser) -> RuntimeSettingsRead:
    """Return safe runtime settings."""
    if current_user.role != UserRole.ADMIN:
        raise AppException(status_code=403, message="Only ADMIN can view runtime settings.")

    AuditService.record(
        db=db,
        action=AuditAction.SETTINGS_VIEW,
        user_id=current_user.id,
        entity_type="settings",
        entity_id=None,
        details={"scope": "runtime"},
    )
    db.commit()
    return SettingsService.read_runtime_settings()
