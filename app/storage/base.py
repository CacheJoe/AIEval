"""Storage abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class StoredArtifact:
    """Saved artifact metadata."""

    absolute_path: Path
    relative_path: str
    size_bytes: int


class StorageProvider(ABC):
    """Abstract storage interface."""

    @abstractmethod
    def save_bytes(self, relative_path: str, content: bytes) -> StoredArtifact:
        """Persist raw bytes and return saved artifact metadata."""

    @abstractmethod
    def read_bytes(self, relative_path: str) -> bytes:
        """Load bytes from storage."""

    @abstractmethod
    def resolve_path(self, relative_path: str) -> Path:
        """Resolve a relative storage path to a concrete filesystem path."""

