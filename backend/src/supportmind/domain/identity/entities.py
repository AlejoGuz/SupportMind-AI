from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from supportmind.domain.common.base import entity_id, utcnow
from supportmind.domain.common.enums import AgentAvailability, AgentRole


@dataclass
class Agent:
    email: str
    full_name: str
    hashed_password: str
    roles: list = field(default_factory=lambda: [AgentRole.AGENT_L1])
    availability: AgentAvailability = AgentAvailability.AVAILABLE
    is_active: bool = True
    open_ticket_count: int = 0
    id: UUID = field(default_factory=entity_id)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def touch(self) -> None:
        self.updated_at = utcnow()

    def is_l1_available(self) -> bool:
        return (
            self.is_active
            and self.availability == AgentAvailability.AVAILABLE
            and AgentRole.AGENT_L1 in self.roles
        )
