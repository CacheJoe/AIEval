"""Local filesystem storage implementation."""

from __future__ import annotations

from pathlib import Path

from app.storage.base import StorageProvider, StoredArtifact
from app.utils.config import get_settings


class LocalStorageProvider(StorageProvider):
    """Persist artifacts to the local filesystem."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.settings.ensure_directories()

    def save_bytes(self, relative_path: str, content: bytes) -> StoredArtifact:
        path = self.resolve_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return StoredArtifact(
            absolute_path=path,
            relative_path=relative_path.replace("\\", "/"),
            size_bytes=len(content),
        )

    def read_bytes(self, relative_path: str) -> bytes:
        return self.resolve_path(relative_path).read_bytes()

    def resolve_path(self, relative_path: str) -> Path:
        normalized = relative_path.replace("\\", "/").lstrip("/")
        return Path(self.settings.submissions_dir.parent, normalized)

