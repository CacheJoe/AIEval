"""Storage provider resolver."""

from __future__ import annotations

from functools import lru_cache

from app.storage.base import StorageProvider
from app.storage.local import LocalStorageProvider
from app.utils.config import get_settings


@lru_cache(maxsize=1)
def get_storage_provider() -> StorageProvider:
    """Return the configured storage provider."""
    settings = get_settings()
    if settings.storage_backend == "local":
        return LocalStorageProvider()
    raise ValueError(f"Unsupported storage backend: {settings.storage_backend}")

