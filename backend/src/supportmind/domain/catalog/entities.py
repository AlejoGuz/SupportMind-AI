from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from supportmind.domain.common.base import entity_id, utcnow


@dataclass
class Product:
    sku: str
    name: str
    family: str
    brand: str
    is_active: bool = True
    id: UUID = field(default_factory=entity_id)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class AuditEntry:
    action: str
    actor: str
    resource_type: str
    resource_id: str
    details: dict
    id: UUID = field(default_factory=entity_id)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
