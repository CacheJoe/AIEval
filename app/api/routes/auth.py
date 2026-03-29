"""Authentication API routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshTokenRequest, TokenResponse
from app.schemas.common import MessageResponse
from app.schemas.user import UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(request_data: LoginRequest, request: Request, db: DBSession) -> TokenResponse:
    """Authenticate a user and issue a fresh access/refresh token pair."""
    user = AuthService.authenticate_user(db, request_data.email, request_data.password)
    token_pair = AuthService.issue_token_pair(
        db=db,
        user=user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        access_token_expires_at=token_pair.access_token_expires_at,
        refresh_token_expires_at=token_pair.refresh_token_expires_at,
        user=UserRead.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def refresh_tokens(
    request_data: RefreshTokenRequest,
    request: Request,
    db: DBSession,
) -> TokenResponse:
    """Rotate a refresh token and return a new token pair."""
    user, token_pair = AuthService.rotate_refresh_token(
        db=db,
        refresh_token=request_data.refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        access_token_expires_at=token_pair.access_token_expires_at,
        refresh_token_expires_at=token_pair.refresh_token_expires_at,
        user=UserRead.model_validate(user),
    )


@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def logout(request_data: LogoutRequest, request: Request, db: DBSession) -> MessageResponse:
    """Revoke a refresh token and terminate the active session."""
    AuthService.logout(
        db=db,
        refresh_token=request_data.refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return MessageResponse(message="Session terminated successfully.")


@router.get("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
def get_current_profile(current_user: CurrentUser) -> UserRead:
    """Return the authenticated user's profile."""
    return UserRead.model_validate(current_user)

