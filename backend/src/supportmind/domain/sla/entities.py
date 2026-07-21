from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from supportmind.domain.common.base import entity_id, utcnow
from supportmind.domain.common.enums import Priority


@dataclass
class SlaPolicy:
    priority: Priority
    response_minutes: int
    resolution_minutes: int
    is_active: bool = True
    id: UUID = field(default_factory=entity_id)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class TicketSlaClock:
    ticket_id: UUID
    priority: Priority
    response_due_at: datetime
    resolution_due_at: datetime
    response_breached: bool = False
    resolution_breached: bool = False
    id: UUID = field(default_factory=entity_id)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    @staticmethod
    def start(ticket_id: UUID, policy: SlaPolicy) -> "TicketSlaClock":
        now = utcnow()
        return TicketSlaClock(
            ticket_id=ticket_id,
            priority=policy.priority,
            response_due_at=now + timedelta(minutes=policy.response_minutes),
            resolution_due_at=now + timedelta(minutes=policy.resolution_minutes),
        )

    def remaining_seconds(self) -> int:
        return max(0, int((self.resolution_due_at - utcnow()).total_seconds()))
