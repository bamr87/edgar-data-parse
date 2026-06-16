"""Pluggable, content-addressed blob storage for filing artifacts.

Artifacts (raw filing documents, extracted text) are addressed by the SHA-1 of
their content, so identical bytes are stored once. The default LOCAL backend
writes under ``STORAGE_ROOT``; an optional S3 backend is selected via
``STORAGE_BACKEND=s3`` (requires ``boto3``). Modeled on OpenEDGAR's
``clients/{local,s3}.py`` (MIT), modernized to a single interface.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol

from django.conf import settings


def content_sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


class Storage(Protocol):
    def exists(self, key: str) -> bool: ...
    def put_bytes(self, key: str, data: bytes) -> None: ...
    def get_bytes(self, key: str) -> bytes: ...


class LocalStorage:
    """Filesystem backend rooted at ``root`` (default: ``STORAGE_ROOT``)."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        return self.root / key

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def put_bytes(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()


class S3Storage:
    """S3 backend (lazy boto3 import; only used when STORAGE_BACKEND=s3)."""

    def __init__(self, bucket: str, prefix: str = "") -> None:
        try:
            import boto3  # noqa: PLC0415
        except ImportError as e:  # pragma: no cover - exercised only with S3 selected
            raise RuntimeError(
                "STORAGE_BACKEND=s3 requires boto3 (pip install boto3)."
            ) from e
        self._s3 = boto3.client("s3")
        self.bucket = bucket
        self.prefix = prefix.strip("/")

    def _full(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError  # noqa: PLC0415

        try:
            self._s3.head_object(Bucket=self.bucket, Key=self._full(key))
            return True
        except ClientError:
            return False

    def put_bytes(self, key: str, data: bytes) -> None:
        self._s3.put_object(Bucket=self.bucket, Key=self._full(key), Body=data)

    def get_bytes(self, key: str) -> bytes:
        obj = self._s3.get_object(Bucket=self.bucket, Key=self._full(key))
        return obj["Body"].read()


def get_storage() -> Storage:
    backend = getattr(settings, "STORAGE_BACKEND", "local").lower()
    if backend == "s3":
        return S3Storage(settings.S3_BUCKET, getattr(settings, "S3_PREFIX", ""))
    return LocalStorage(getattr(settings, "STORAGE_ROOT", settings.EDGAR_DATA_DIR))


def store_content(data: bytes, *, prefix: str, storage: Storage | None = None) -> str:
    """Store ``data`` content-addressed by SHA-1 under ``prefix/``; returns the key.

    Idempotent: identical bytes resolve to the same key and are written only once.
    """
    storage = storage or get_storage()
    key = f"{prefix}/{content_sha1(data)}"
    if not storage.exists(key):
        storage.put_bytes(key, data)
    return key
