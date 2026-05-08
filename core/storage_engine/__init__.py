"""
儲存引擎抽象層 — 統一 Local FS / MinIO(S3) 介面

所有服務透過此層存取物件儲存，實作可無縫切換。
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO


class StorageBackend(ABC):
    @abstractmethod
    async def put(self, bucket: str, key: str, data: BinaryIO, content_type: str = "application/octet-stream") -> str:
        """上傳物件，回傳可存取 URL 或 key"""

    @abstractmethod
    async def get(self, bucket: str, key: str) -> bytes:
        """下載物件"""

    @abstractmethod
    async def delete(self, bucket: str, key: str) -> None:
        """刪除物件"""

    @abstractmethod
    async def presign_get(self, bucket: str, key: str, expires: int = 3600) -> str:
        """產生簽名下載 URL"""

    @abstractmethod
    async def presign_put(self, bucket: str, key: str, expires: int = 300) -> str:
        """產生簽名上傳 URL"""

    @abstractmethod
    async def exists(self, bucket: str, key: str) -> bool:
        """檢查物件是否存在"""


# Bucket 常數
class Buckets:
    UPLOADS    = "xcloudpdf-uploads"
    PROCESSED  = "xcloudpdf-processed"
    PREVIEWS   = "xcloudpdf-previews"
    TEMPLATES  = "xcloudpdf-templates"
    ASSETS     = "xcloudpdf-assets"
    AUDIT_EXPORT = "xcloudpdf-audit-export"


def get_storage() -> StorageBackend:
    """工廠函數：依環境變數選擇後端"""
    backend = os.getenv("STORAGE_BACKEND", "minio")
    if backend == "minio" or backend == "s3":
        from .minio_backend import MinioBackend
        return MinioBackend()
    from .local_backend import LocalBackend
    return LocalBackend()
