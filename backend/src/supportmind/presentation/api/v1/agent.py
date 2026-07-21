from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from supportmind.application.use_cases.alerting import (
    AcceptAlertRequest,
    CreateManualIncident,
    GetAlertDetail,
    RejectAlertRequest,
    ResolveIncident,
)
from supportmind.application.use_cases.auth import LoginAgent
from supportmind.dependencies import (
    Container,
    accept_alert_uc,
    alert_detail_uc,
    get_container,
    get_current_agent_id,
    login_uc,
    manual_incident_uc,
    reject_alert_uc,
    resolve_incident_uc,
)
from supportmind.domain.common.base import DomainError
from supportmind.domain.common.enums import TicketStatus
from supportmind.domain.ticketing.entities import TicketEvent
from supportmind.infrastructure.auth.security import refresh_access_token
from supportmind.presentation.api.v1.public import _domain_http, _ticket_out
from supportmind.presentation.schemas.api import (
    AcceptAlertBody,
    AgentOut,
    AlertDetailOut,
    AlertOut,
    AlertTicketDetailOut,
    AuditOut,
    CommentRequest,
    IncidentOut,
    LoginRequest,
    ManualIncidentRequest,
    MetricsOverview,
    RefreshRequest,
    RejectAlertRequest as RejectBody,
    TokenResponse,
    TransitionRequest,
)

router = APIRouter(tags=["agent"])


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, uc: LoginAgent = Depends(login_uc)):
    try:
        result = await uc.execute(email=str(body.email), password=body.password)
        tokens = result["tokens"]
        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
        )
    except DomainError as exc:
        raise _domain_http(exc) from exc


@router.post("/auth/refresh")
async def refresh(body: RefreshRequest):
    try:
        return refresh_access_token(body.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc


@router.get("/agents/me", response_model=AgentOut)
async def me(
    agent_id: str = Depends(get_current_agent_id),
    c: Container = Depends(get_container),
):
    agent = await c.agents.get_by_id(UUID(agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentOut(
        id=agent.id,
        email=agent.email,
        full_name=agent.full_name,
        roles=[r.value for r in agent.roles],
        availability=agent.availability.value,
        is_active=agent.is_active,
        open_ticket_count=agent.open_ticket_count,
    )


@router.get("/agents", response_model=list[AgentOut])
async def list_agents(
    _: str = Depends(get_current_agent_id),
    c: Container = Depends(get_container),
):
    agents = await c.agents.list_agents()
    return [
        AgentOut(
            id=a.id,
            email=a.email,
            full_name=a.full_name,
            roles=[r.value for r in a.roles],
            availability=a.availability.value,
            is_active=a.is_active,
            open_ticket_count=a.open_ticket_count,
        )
        for a in agents
    ]


@router.get("/tickets")
async def list_tickets(
    status: str | None = None,
    _: str = Depends(get_current_agent_id),
    c: Container = Depends(get_container),
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    tickets = await c.tickets.list_tickets(status=status, limit=limit, offset=offset)
    out = []
    for t in tickets:
        clock = await c.sla.get_clock(t.id)
        out.append(_ticket_out(t, clock.remaining_seconds() if clock else None))
    return out


@router.get("/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: UUID,
    _: str = Depends(get_current_agent_id),
    c: Container = Depends(get_container),
):
    ticket = await c.tickets.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    clock = await c.sla.get_clock(ticket.id)
    return _ticket_out(ticket, clock.remaining_seconds() if clock else None)


@router.post("/tickets/{ticket_id}/transitions")
async def transition_ticket(
    ticket_id: UUID,
    body: TransitionRequest,
    agent_id: str = Depends(get_current_agent_id),
    c: Container = Depends(get_container),
):
    ticket = await c.tickets.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    try:
        new_status = TicketStatus(body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid status") from exc
    ticket.transition(new_status)
    ticket.events.append(
        TicketEvent(
            id=uuid4(),
            event_type="status_changed",
            message=f"Estado cambiado a {new_status.value}",
            actor=agent_id,
        )
    )
    ticket = await c.tickets.save(ticket)
    return _ticket_out(ticket)


@router.post("/tickets/{ticket_id}/comments")
async def comment_ticket(
    ticket_id: UUID,
    body: CommentRequest,
    agent_id: str = Depends(get_current_agent_id),
    c: Container = Depends(get_container),
):
    ticket = await c.tickets.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.events.append(
        TicketEvent(
            id=uuid4(),
            event_type="comment",
            message=body.message,
            actor=agent_id,
        )
    )
    ticket = await c.tickets.save(ticket)
    return _ticket_out(ticket)


@router.get("/alerts", response_model=list[AlertOut])
async def list_alerts(
    _: str = Depends(get_current_agent_id),
    c: Container = Depends(get_container),
):
    alerts = await c.alerts.list_pending()
    return [
        AlertOut(
            id=a.id,
            fingerprint=a.fingerprint,
            problem_code=a.problem_code,
            ticket_count=a.ticket_count,
            window_seconds=a.window_seconds,
            status=a.status.value,
            public_title=a.public_title,
            ticket_ids=a.ticket_ids,
            created_at=a.created_at,
        )
        for a in alerts
    ]


@router.post("/alerts/manual", response_model=IncidentOut)
async def create_manual_incident(
    body: ManualIncidentRequest,
    agent_id: str = Depends(get_current_agent_id),
    uc: CreateManualIncident = Depends(manual_incident_uc),
):
    try:
        incident = await uc.execute(
            agent_id=UUID(agent_id),
            title=body.title,
            problem_code=body.problem_code,
            public_message=body.public_message,
            fingerprint=body.fingerprint,
            escalation_level=body.escalation_level,
            link_existing_fingerprint=body.link_existing_fingerprint,
        )
        return _incident_out(incident)
    except DomainError as exc:
        raise _domain_http(exc) from exc


@router.get("/alerts/{alert_id}/detail", response_model=AlertDetailOut)
async def alert_detail(
    alert_id: UUID,
    _: str = Depends(get_current_agent_id),
    uc: GetAlertDetail = Depends(alert_detail_uc),
):
    try:
        view = await uc.execute(alert_id=alert_id)
        return AlertDetailOut(
            id=view.id,
            fingerprint=view.fingerprint,
            problem_code=view.problem_code,
            ticket_count=view.ticket_count,
            window_seconds=view.window_seconds,
            status=view.status,
            public_title=view.public_title,
            created_at=view.created_at,
            reason=view.reason,
            tickets=[
                AlertTicketDetailOut(
                    id=t.id,
                    number=t.number,
                    status=t.status,
                    priority=t.priority,
                    customer_name=t.customer_name,
                    customer_email=t.customer_email,
                    summary_ai=t.summary_ai,
                    description=t.description,
                    created_at=t.created_at,
                )
                for t in view.tickets
            ],
        )
    except DomainError as exc:
        raise _domain_http(exc) from exc


def _incident_out(incident, child_tickets=None) -> IncidentOut:
    return IncidentOut(
        id=incident.id,
        number=incident.number,
        title=incident.title,
        fingerprint=incident.fingerprint,
        problem_code=incident.problem_code,
        status=incident.status.value,
        public_message=incident.public_message,
        ticket_ids=incident.ticket_ids,
        created_at=incident.created_at,
        resolved_at=incident.resolved_at,
        escalation_level=getattr(incident, "escalation_level", "l2") or "l2",
        is_parent=True,
        child_tickets=child_tickets,
    )


@router.post("/alerts/{alert_id}/accept", response_model=IncidentOut)
async def accept_alert(
    alert_id: UUID,
    body: AcceptAlertBody = AcceptAlertBody(),
    agent_id: str = Depends(get_current_agent_id),
    uc: AcceptAlertRequest = Depends(accept_alert_uc),
):
    try:
        level = body.escalation_level or "l2"
        incident = await uc.execute(
            alert_id=alert_id, agent_id=UUID(agent_id), escalation_level=level
        )
        return _incident_out(incident)
    except DomainError as exc:
        raise _domain_http(exc) from exc


@router.post("/alerts/{alert_id}/reject")
async def reject_alert(
    alert_id: UUID,
    body: RejectBody,
    agent_id: str = Depends(get_current_agent_id),
    uc: RejectAlertRequest = Depends(reject_alert_uc),
):
    try:
        decision = await uc.execute(alert_id=alert_id, agent_id=UUID(agent_id), reason=body.reason)
        return {
            "id": str(decision.id),
            "decision": decision.decision.value,
            "reason": decision.reason,
            "ticket_count_snapshot": decision.ticket_count_snapshot,
            "decided_at": decision.decided_at.isoformat(),
        }
    except DomainError as exc:
        raise _domain_http(exc) from exc


@router.get("/incidents", response_model=list[IncidentOut])
async def list_incidents(
    status: str | None = None,
    _: str = Depends(get_current_agent_id),
    c: Container = Depends(get_container),
):
    incidents = await c.incidents.list_incidents(status=status)
    return [_incident_out(i) for i in incidents]


@router.get("/incidents/{incident_id}", response_model=IncidentOut)
async def get_incident(
    incident_id: UUID,
    _: str = Depends(get_current_agent_id),
    c: Container = Depends(get_container),
):
    incident = await c.incidents.get_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    children = await c.tickets.list_by_ids(incident.ticket_ids)
    child_out = []
    for t in children:
        clock = await c.sla.get_clock(t.id)
        child_out.append(_ticket_out(t, clock.remaining_seconds() if clock else None))
    return _incident_out(incident, child_tickets=child_out)


@router.post("/incidents/{incident_id}/resolve", response_model=IncidentOut)
async def resolve_incident(
    incident_id: UUID,
    agent_id: str = Depends(get_current_agent_id),
    uc: ResolveIncident = Depends(resolve_incident_uc),
):
    try:
        incident = await uc.execute(incident_id=incident_id, agent_id=UUID(agent_id))
        return _incident_out(incident)
    except DomainError as exc:
        raise _domain_http(exc) from exc


@router.get("/metrics/overview", response_model=MetricsOverview)
async def metrics(
    _: str = Depends(get_current_agent_id),
    c: Container = Depends(get_container),
):
    tickets = await c.tickets.list_tickets(limit=500)
    alerts = await c.alerts.list_pending()
    incidents = await c.incidents.list_active_public()
    by_priority: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for t in tickets:
        by_priority[t.priority.value] = by_priority.get(t.priority.value, 0) + 1
        by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
    return MetricsOverview(
        open_tickets=by_status.get("open", 0) + by_status.get("new", 0),
        new_tickets=by_status.get("new", 0),
        pending_alerts=len(alerts),
        active_incidents=len(incidents),
        resolved_today=by_status.get("resolved", 0),
        avg_priority_p1=by_priority.get("P1", 0),
        tickets_by_priority=by_priority,
        tickets_by_status=by_status,
    )


@router.get("/audit", response_model=list[AuditOut])
async def audit_trail(
    _: str = Depends(get_current_agent_id),
    c: Container = Depends(get_container),
    limit: int = Query(100, le=500),
):
    entries = await c.audit.list_recent(limit=limit)
    return [
        AuditOut(
            id=e.id,
            action=e.action,
            actor=e.actor,
            resource_type=e.resource_type,
            resource_id=e.resource_id,
            details=e.details,
            created_at=e.created_at,
        )
        for e in entries
    ]


@router.get("/admin/sla-policies")
async def sla_policies(
    _: str = Depends(get_current_agent_id),
    c: Container = Depends(get_container),
):
    policies = await c.sla.list_policies()
    return [
        {
            "id": str(p.id),
            "priority": p.priority.value,
            "response_minutes": p.response_minutes,
            "resolution_minutes": p.resolution_minutes,
            "is_active": p.is_active,
        }
        for p in policies
    ]


@router.get("/admin/decision-trees")
async def decision_trees(
    _: str = Depends(get_current_agent_id),
    c: Container = Depends(get_container),
):
    trees = await c.trees.list_trees()
    return [
        {
            "id": str(t.id),
            "slug": t.slug,
            "name": t.name,
            "version": t.version,
            "is_active": t.is_active,
            "description": t.description,
        }
        for t in trees
    ]
