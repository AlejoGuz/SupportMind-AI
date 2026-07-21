from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DomainError(Exception):
    code: str
    message: str
    details: Optional[dict] = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def entity_id() -> UUID:
    return uuid4()
