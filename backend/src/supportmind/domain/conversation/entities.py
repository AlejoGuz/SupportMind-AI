from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from supportmind.domain.common.base import entity_id, utcnow
from supportmind.domain.common.enums import ConversationOutcome, NodeType


@dataclass
class DecisionOption:
    id: UUID
    label: str
    next_node_id: Optional[UUID]
    sort_order: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class DecisionNode:
    tree_id: UUID
    code: str
    prompt: str
    node_type: NodeType
    options: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    id: UUID = field(default_factory=entity_id)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def touch(self) -> None:
        self.updated_at = utcnow()


@dataclass
class DecisionTree:
    slug: str
    name: str
    version: int
    is_active: bool
    root_node_id: Optional[UUID]
    description: str = ""
    id: UUID = field(default_factory=entity_id)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def touch(self) -> None:
        self.updated_at = utcnow()


@dataclass
class ConversationStep:
    node_id: UUID
    node_code: str
    option_id: Optional[UUID]
    option_label: Optional[str]
    prompt: str


@dataclass
class ConversationSession:
    public_token: str
    tree_id: UUID
    tree_version: int
    current_node_id: UUID
    path: list = field(default_factory=list)
    outcome: Optional[ConversationOutcome] = None
    product_id: Optional[UUID] = None
    ended_at: Optional[datetime] = None
    id: UUID = field(default_factory=entity_id)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def touch(self) -> None:
        self.updated_at = utcnow()

    def record_step(
        self,
        *,
        node_id: UUID,
        node_code: str,
        prompt: str,
        option_id: Optional[UUID],
        option_label: Optional[str],
        next_node_id: UUID,
    ) -> None:
        self.path.append(
            ConversationStep(
                node_id=node_id,
                node_code=node_code,
                option_id=option_id,
                option_label=option_label,
                prompt=prompt,
            )
        )
        self.current_node_id = next_node_id
        self.touch()

    def complete(self, outcome: ConversationOutcome) -> None:
        self.outcome = outcome
        self.ended_at = utcnow()
        self.touch()
