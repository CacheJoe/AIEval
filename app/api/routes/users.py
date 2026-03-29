"""User administration routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, status

from app.api.deps import DBSession
from app.auth.dependencies import require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserStatusUpdate
from app.services.audit_service import AuditService
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[UserRead], status_code=status.HTTP_200_OK)
def list_users(
    db: DBSession,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[UserRead]:
    """List platform users for administrators."""
    users = UserService.list_users(db)
    return [UserRead.model_validate(user) for user in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: DBSession,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> UserRead:
    """Create a new user account."""
    user = UserService.create_user(db=db, payload=payload)
    AuditService.record(
        db=db,
        action="USER_CREATE",
        user_id=current_user.id,
        details={"created_user_id": user.id, "email": user.email, "role": user.role.value},
    )
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.patch(
    "/{user_id}/status",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
def update_user_status(
    payload: UserStatusUpdate,
    db: DBSession,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    user_id: str = Path(..., min_length=36, max_length=36),
) -> UserRead:
    """Activate or deactivate a user account."""
    user = UserService.update_status(db=db, user_id=user_id, is_active=payload.is_active)
    AuditService.record(
        db=db,
        action="USER_STATUS_UPDATE",
        user_id=current_user.id,
        details={"target_user_id": user.id, "is_active": user.is_active},
    )
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)

