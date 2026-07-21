from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from supportmind.domain.common.base import entity_id, utcnow
from supportmind.domain.common.enums import AlertDecisionType, AlertRequestStatus, IncidentStatus


@dataclass
class AlertRequest:
    fingerprint: str
    problem_code: str
    ticket_count: int
    window_seconds: int
    status: AlertRequestStatus = AlertRequestStatus.PENDING
    ticket_ids: list = field(default_factory=list)
    public_title: str = ""
    id: UUID = field(default_factory=entity_id)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def touch(self) -> None:
        self.updated_at = utcnow()

    def accept(self) -> None:
        self.status = AlertRequestStatus.ACCEPTED
        self.touch()

    def reject(self) -> None:
        self.status = AlertRequestStatus.REJECTED
        self.touch()


@dataclass
class AlertRequestDecision:
    alert_request_id: UUID
    decision: AlertDecisionType
    reason: str
    decided_by: UUID
    ticket_count_snapshot: int
    decided_at: datetime = field(default_factory=utcnow)
    id: UUID = field(default_factory=entity_id)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class Incident:
    number: str
    title: str
    fingerprint: str
    problem_code: str
    status: IncidentStatus
    public_message: str
    created_from_alert_id: Optional[UUID]
    created_by: UUID
    ticket_ids: list = field(default_factory=list)
    resolved_at: Optional[datetime] = None
    id: UUID = field(default_factory=entity_id)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def touch(self) -> None:
        self.updated_at = utcnow()

    def resolve(self) -> None:
        self.status = IncidentStatus.RESOLVED
        self.resolved_at = utcnow()
        self.touch()

    def add_ticket(self, ticket_id: UUID) -> None:
        if ticket_id not in self.ticket_ids:
            self.ticket_ids.append(ticket_id)
            self.touch()
