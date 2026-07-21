from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from supportmind.domain.common.base import entity_id, utcnow
from supportmind.domain.common.enums import Channel, Priority, Sentiment, TicketStatus


@dataclass
class TicketAttachment:
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    storage_key: str
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class TicketEvent:
    id: UUID
    event_type: str
    message: str
    actor: str
    payload: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class Ticket:
    number: str
    status: TicketStatus
    priority: Priority
    category: str
    sentiment: Sentiment
    summary_ai: str
    customer_first_name: str
    customer_last_name: str
    customer_email: str
    customer_phone: str
    order_number: str
    product_id: UUID
    description: str
    channel: Channel
    created_by: str
    problem_fingerprint: str
    conversation_session_id: UUID
    assignee_id: Optional[UUID] = None
    incident_id: Optional[UUID] = None
    attachments: list = field(default_factory=list)
    events: list = field(default_factory=list)
    conversation_transcript: list = field(default_factory=list)
    id: UUID = field(default_factory=entity_id)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def touch(self) -> None:
        self.updated_at = utcnow()

    def assign(self, agent_id: UUID) -> None:
        self.assignee_id = agent_id
        if self.status == TicketStatus.NEW:
            self.status = TicketStatus.OPEN
        self.touch()

    def link_incident(self, incident_id: UUID) -> None:
        self.incident_id = incident_id
        self.touch()

    def transition(self, new_status: TicketStatus) -> None:
        self.status = new_status
        self.touch()
