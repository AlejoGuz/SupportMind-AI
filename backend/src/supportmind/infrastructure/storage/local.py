from __future__ import annotations

import uuid
from pathlib import Path

from supportmind.config import get_settings


class LocalObjectStorage:
    """Filesystem storage for local/dev; MinIO/S3 adapter can replace this port."""

    def __init__(self, base_dir: str | None = None) -> None:
        settings = get_settings()
        self.base = Path(base_dir or "/tmp/supportmind-storage")
        self.base.mkdir(parents=True, exist_ok=True)
        (self.base / settings.s3_bucket_attachments).mkdir(exist_ok=True)
        (self.base / settings.s3_bucket_screenshots).mkdir(exist_ok=True)

    async def upload(self, *, bucket: str, key: str | None = None, data: bytes, content_type: str) -> str:
        object_key = key or f"{uuid.uuid4().hex}"
        path = self.base / bucket / object_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"{bucket}/{object_key}"

    async def generate_presigned_url(self, *, bucket: str, key: str, expires_in: int = 3600) -> str:
        return f"/files/{bucket}/{key}?expires={expires_in}"
