from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, List
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AgentModel(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    roles: Mapped[list] = mapped_column(JSON, default=list)
    availability: Mapped[str] = mapped_column(String(32), default="available")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    open_ticket_count: Mapped[int] = mapped_column(Integer, default=0)


class ProductModel(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    family: Mapped[str] = mapped_column(String(128))
    brand: Mapped[str] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DecisionTreeModel(Base, TimestampMixin):
    __tablename__ = "decision_trees"

    id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(255))
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    root_node_id: Mapped[Optional[Any]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")

    nodes: Mapped[List["DecisionNodeModel"]] = relationship(back_populates="tree")


class DecisionNodeModel(Base, TimestampMixin):
    __tablename__ = "decision_nodes"

    id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tree_id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), ForeignKey("decision_trees.id"))
    code: Mapped[str] = mapped_column(String(128))
    prompt: Mapped[str] = mapped_column(Text)
    node_type: Mapped[str] = mapped_column(String(32))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    tree: Mapped[DecisionTreeModel] = relationship(back_populates="nodes")
    options: Mapped[List["DecisionOptionModel"]] = relationship(back_populates="node")


class DecisionOptionModel(Base):
    __tablename__ = "decision_options"

    id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    node_id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), ForeignKey("decision_nodes.id"))
    label: Mapped[str] = mapped_column(String(255))
    next_node_id: Mapped[Optional[Any]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    node: Mapped[DecisionNodeModel] = relationship(back_populates="options")


class ConversationSessionModel(Base, TimestampMixin):
    __tablename__ = "conversation_sessions"

    id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    public_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    tree_id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), ForeignKey("decision_trees.id"))
    tree_version: Mapped[int] = mapped_column(Integer)
    current_node_id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True))
    path_json: Mapped[list] = mapped_column(JSON, default=list)
    outcome: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    product_id: Mapped[Optional[Any]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class TicketModel(Base, TimestampMixin):
    __tablename__ = "tickets"

    id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    priority: Mapped[str] = mapped_column(String(8), index=True)
    category: Mapped[str] = mapped_column(String(128))
    sentiment: Mapped[str] = mapped_column(String(32))
    summary_ai: Mapped[str] = mapped_column(Text, default="")
    customer_first_name: Mapped[str] = mapped_column(String(128))
    customer_last_name: Mapped[str] = mapped_column(String(128))
    customer_email: Mapped[str] = mapped_column(String(255))
    customer_phone: Mapped[str] = mapped_column(String(64))
    order_number: Mapped[str] = mapped_column(String(64))
    product_id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id"))
    description: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(32), default="celu_chat")
    created_by: Mapped[str] = mapped_column(String(64), default="CELU_BOT")
    assignee_id: Mapped[Optional[Any]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    conversation_session_id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True))
    problem_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    incident_id: Mapped[Optional[Any]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("incidents.id"), nullable=True)
    conversation_transcript: Mapped[list] = mapped_column(JSON, default=list)
    attachments_json: Mapped[list] = mapped_column(JSON, default=list)
    events_json: Mapped[list] = mapped_column(JSON, default=list)


class TicketSequenceModel(Base):
    __tablename__ = "ticket_sequences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, unique=True)
    last_value: Mapped[int] = mapped_column(Integer, default=0)


class IncidentSequenceModel(Base):
    __tablename__ = "incident_sequences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, unique=True)
    last_value: Mapped[int] = mapped_column(Integer, default=0)


class SlaPolicyModel(Base, TimestampMixin):
    __tablename__ = "sla_policies"

    id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    priority: Mapped[str] = mapped_column(String(8), unique=True)
    response_minutes: Mapped[int] = mapped_column(Integer)
    resolution_minutes: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TicketSlaClockModel(Base, TimestampMixin):
    __tablename__ = "ticket_sla_clocks"

    id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    ticket_id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), unique=True, index=True)
    priority: Mapped[str] = mapped_column(String(8))
    response_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolution_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    response_breached: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_breached: Mapped[bool] = mapped_column(Boolean, default=False)


class AlertRequestModel(Base, TimestampMixin):
    __tablename__ = "alert_requests"

    id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    problem_code: Mapped[str] = mapped_column(String(128))
    ticket_count: Mapped[int] = mapped_column(Integer)
    window_seconds: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), index=True)
    ticket_ids: Mapped[list] = mapped_column(JSON, default=list)
    public_title: Mapped[str] = mapped_column(Text, default="")


class AlertRequestDecisionModel(Base, TimestampMixin):
    __tablename__ = "alert_request_decisions"

    id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    alert_request_id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), ForeignKey("alert_requests.id"))
    decision: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(Text)
    decided_by: Mapped[Any] = mapped_column(PGUUID(as_uuid=True))
    ticket_count_snapshot: Mapped[int] = mapped_column(Integer)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IncidentModel(Base, TimestampMixin):
    __tablename__ = "incidents"

    id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    problem_code: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), index=True)
    public_message: Mapped[str] = mapped_column(Text)
    created_from_alert_id: Mapped[Optional[Any]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_by: Mapped[Any] = mapped_column(PGUUID(as_uuid=True))
    ticket_ids: Mapped[list] = mapped_column(JSON, default=list)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLogModel(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    action: Mapped[str] = mapped_column(String(128), index=True)
    actor: Mapped[str] = mapped_column(String(128))
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class AiEnrichmentModel(Base, TimestampMixin):
    __tablename__ = "ai_enrichments"

    id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    ticket_id: Mapped[Optional[Any]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    prompt_version: Mapped[str] = mapped_column(String(32))
    priority: Mapped[str] = mapped_column(String(8))
    category: Mapped[str] = mapped_column(String(128))
    sentiment: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(Text)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
