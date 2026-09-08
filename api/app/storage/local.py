"""Local-disk implementation of StorageBackend."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from app.storage.base import StorageBackend


class LocalDiskStorage(StorageBackend):
    """
    Stores files under *root* on the local filesystem.

    Directory layout: {root}/{key}
    URL layout:      {base_url}/{key}

    To move to Cloudflare R2: implement StorageBackend using boto3/cloudflare-sdk.
    The rest of the application is unchanged.
    """

    def __init__(self, root: str, base_url: str) -> None:
        self._root = Path(root)
        self._base_url = base_url.rstrip("/")

    def _abs(self, key: str) -> Path:
        """Resolve key to an absolute path, preventing path traversal."""
        resolved = (self._root / key).resolve()
        if not str(resolved).startswith(str(self._root.resolve())):
            raise ValueError(f"Path traversal detected for key: {key}")
        return resolved

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        path = self._abs(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        path = self._abs(key)
        if not path.exists():
            raise FileNotFoundError(f"Storage key not found: {key}")
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        try:
            return self._abs(key).exists()
        except ValueError:
            return False

    def url_for(self, key: str) -> str:
        return f"{self._base_url}/{key}"

    def atomic_pointer_write(self, key: str, data: bytes) -> None:
        """
        Write *data* to *key* atomically using write-to-tmp-then-rename.

        A concurrent reader either sees the old content or the new content,
        never a partial write.  This is safe on POSIX (rename is atomic);
        on Windows, os.replace() achieves the same semantic.
        """
        final_path = self._abs(key)
        final_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to a temp file in the same directory (same filesystem → atomic rename)
        tmp_key = f"{key}.{uuid.uuid4().hex}.tmp"
        tmp_path = self._abs(tmp_key)
        try:
            tmp_path.write_bytes(data)
            os.replace(tmp_path, final_path)  # atomic on POSIX and Windows
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
