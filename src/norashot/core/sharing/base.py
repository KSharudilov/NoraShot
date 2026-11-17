from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ShareResult:
    object_key: str
    url: str
    expires_at: datetime


class StorageProvider(ABC):
    """Contract independent of how screenshots are stored and shared."""

    @abstractmethod
    def upload(self, png: bytes) -> ShareResult:
        """Persist PNG and return a usable link."""

    @abstractmethod
    def delete(self, object_key: str) -> None:
        """Remove an already uploaded screenshot."""


class SharingError(RuntimeError):
    """Error intended for display without exposing credentials or signed URLs."""
