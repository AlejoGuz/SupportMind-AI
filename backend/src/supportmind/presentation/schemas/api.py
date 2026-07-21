from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ProblemDetail(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    code: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class StartSessionRequest(BaseModel):
    tree_slug: str = "phone-power"
    product_id: Optional[UUID] = None


class AnswerRequest(BaseModel):
    option_id: UUID


class OptionOut(BaseModel):
    id: str
    label: str
    sort_order: int = 0


class CurrentNodeResponse(BaseModel):
    session_id: UUID
    public_token: str
    node_id: UUID
    node_code: str
    prompt: str
    node_type: str
    options: List[OptionOut]
    outcome: Optional[str] = None
    blocked_message: Optional[str] = None


class EscalateRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    order_number: str
    product_id: UUID
    description: str = Field(min_length=5)
    attachment_keys: Optional[List[Dict[str, Any]]] = None


class TicketOut(BaseModel):
    id: UUID
    number: str
    status: str
    priority: str
    category: str
    sentiment: str
    summary_ai: str
    customer_first_name: str
    customer_last_name: str
    customer_email: str
    customer_phone: str
    order_number: str
    product_id: UUID
    description: str
    channel: str
    created_by: str
    assignee_id: Optional[UUID]
    incident_id: Optional[UUID]
    problem_fingerprint: str
    conversation_transcript: List[Dict[str, Any]]
    attachments: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    sla_remaining_seconds: Optional[int] = None


class ProductOut(BaseModel):
    id: UUID
    sku: str
    name: str
    family: str
    brand: str


class AlertOut(BaseModel):
    id: UUID
    fingerprint: str
    problem_code: str
    ticket_count: int
    window_seconds: int
    status: str
    public_title: str
    ticket_ids: List[UUID]
    created_at: datetime


class RejectAlertRequest(BaseModel):
    reason: str = Field(min_length=3)


class IncidentOut(BaseModel):
    id: UUID
    number: str
    title: str
    fingerprint: str
    problem_code: str
    status: str
    public_message: str
    ticket_ids: List[UUID]
    created_at: datetime
    resolved_at: Optional[datetime]


class AgentOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    roles: List[str]
    availability: str
    is_active: bool
    open_ticket_count: int


class MetricsOverview(BaseModel):
    open_tickets: int
    new_tickets: int
    pending_alerts: int
    active_incidents: int
    resolved_today: int
    avg_priority_p1: int
    tickets_by_priority: Dict[str, int]
    tickets_by_status: Dict[str, int]


class AuditOut(BaseModel):
    id: UUID
    action: str
    actor: str
    resource_type: str
    resource_id: str
    details: Dict[str, Any]
    created_at: datetime


class TransitionRequest(BaseModel):
    status: str


class CommentRequest(BaseModel):
    message: str
