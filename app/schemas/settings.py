"""Settings schemas."""

from __future__ import annotations

from pydantic import BaseModel


class RuntimeSettingsRead(BaseModel):
    """Read-only runtime settings."""

    environment: str
    database_url: str
    upload_limits: dict[str, object]
    thresholds: dict[str, float]
    scoring: dict[str, float]
    storage_backend: str
    semantic_model_name: str

