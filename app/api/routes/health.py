"""Health check routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, status

from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
def healthcheck() -> HealthResponse:
    """Return a simple API health payload."""
    return HealthResponse(status="ok", timestamp=datetime.now(timezone.utc))

