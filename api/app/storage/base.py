"""StorageBackend abstract base class."""
from __future__ import annotations

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """
    Abstract storage interface.

    Swapping from LocalDiskStorage to Cloudflare R2 (or S3) requires only
    implementing this class — application code never touches the filesystem
    directly.
    """

    @abstractmethod
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        """Write *data* to *key*. Overwrites if key already exists."""
        ...

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Read and return raw bytes from *key*. Raises FileNotFoundError if absent."""
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return True if *key* exists in storage."""
        ...

    @abstractmethod
    def url_for(self, key: str) -> str:
        """Return the public URL for *key*."""
        ...

    @abstractmethod
    def atomic_pointer_write(self, key: str, data: bytes) -> None:
        """
        Write *data* to *key* atomically.

        The implementation must guarantee that a concurrent reader never sees
        a partially written file.  On local disk this is achieved with a
        write-to-tmp-then-rename pattern.  On object storage this is achieved
        by the PUT operation itself (object stores are atomic by definition).

        Used to update the current-catalogue pointer after a successful publish.
        """
        ...
