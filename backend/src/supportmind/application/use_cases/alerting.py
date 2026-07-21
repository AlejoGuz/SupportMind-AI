from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from supportmind.application.ports.interfaces import (
    AlertRepositoryPort,
    AuditRepositoryPort,
    IncidentRepositoryPort,
    TicketRepositoryPort,
)
from supportmind.domain.alerting.entities import AlertRequest, AlertRequestDecision, Incident
from supportmind.domain.catalog.entities import AuditEntry
from supportmind.domain.common.base import DomainError, utcnow
from supportmind.domain.common.enums import AlertDecisionType, AlertRequestStatus, IncidentStatus
from supportmind.domain.common.value_objects import IncidentNumber
from supportmind.domain.ticketing.entities import Ticket


@dataclass
class AlertTicketDetail:
    id: UUID
    number: str
    status: str
    priority: str
    customer_name: str
    customer_email: str
    summary_ai: str
    description: str
    created_at: datetime


@dataclass
class AlertDetailView:
    id: UUID
    fingerprint: str
    problem_code: str
    ticket_count: int
    window_seconds: int
    status: str
    public_title: str
    created_at: datetime
    reason: str
    tickets: list[AlertTicketDetail]


class AcceptAlertRequest:
    def __init__(
        self,
        alerts: AlertRepositoryPort,
        incidents: IncidentRepositoryPort,
        tickets: TicketRepositoryPort,
        audit: AuditRepositoryPort,
    ) -> None:
        self._alerts = alerts
        self._incidents = incidents
        self._tickets = tickets
        self._audit = audit

    async def execute(self, *, alert_id: UUID, agent_id: UUID, escalation_level: str = "l2") -> Incident:
        request = await self._alerts.get_request(alert_id)
        if not request:
            raise DomainError("ALERT_NOT_FOUND", "Alert request not found")
        if request.status != AlertRequestStatus.PENDING:
            raise DomainError("ALERT_NOT_PENDING", f"Alert is {request.status}")

        existing = await self._incidents.get_active_by_fingerprint(request.fingerprint)
        if existing:
            raise DomainError("INCIDENT_EXISTS", "Active incident already exists for fingerprint")

        request.accept()
        await self._alerts.save_request(request)

        decision = AlertRequestDecision(
            alert_request_id=request.id,
            decision=AlertDecisionType.ACCEPT,
            reason="Accepted by agent",
            decided_by=agent_id,
            ticket_count_snapshot=request.ticket_count,
        )
        await self._alerts.save_decision(decision)

        related = await self._tickets.list_by_fingerprint(request.fingerprint)
        ticket_ids = [t.id for t in related] if related else list(request.ticket_ids)

        seq = await self._incidents.next_sequence()
        number = IncidentNumber.generate(utcnow().year, seq).value
        level = escalation_level if escalation_level in {"l2", "l3"} else "l2"
        public_message = (
            f"Actualmente existe un incidente conocido relacionado con {request.problem_code.upper()}. "
            "Nuestro equipo ya está trabajando para resolverlo."
        )
        incident = Incident(
            number=number,
            title=f"Ticket padre incidente · {request.problem_code.upper()} · Escalado {level.upper()}",
            fingerprint=request.fingerprint,
            problem_code=request.problem_code,
            status=IncidentStatus.ACTIVE,
            public_message=public_message,
            created_from_alert_id=request.id,
            created_by=agent_id,
            ticket_ids=ticket_ids,
            escalation_level=level,
            is_parent=True,
        )
        incident = await self._incidents.save(incident)
        if ticket_ids:
            await self._tickets.link_to_incident(ticket_ids, incident.id)

        await self._audit.append(
            AuditEntry(
                action="alert_request.accepted",
                actor=str(agent_id),
                resource_type="incident",
                resource_id=str(incident.id),
                details={
                    "alert_id": str(request.id),
                    "ticket_count": len(ticket_ids),
                    "fingerprint": request.fingerprint,
                    "escalation_level": level,
                },
            )
        )
        return incident


class RejectAlertRequest:
    def __init__(
        self,
        alerts: AlertRepositoryPort,
        audit: AuditRepositoryPort,
    ) -> None:
        self._alerts = alerts
        self._audit = audit

    async def execute(self, *, alert_id: UUID, agent_id: UUID, reason: str) -> AlertRequestDecision:
        request = await self._alerts.get_request(alert_id)
        if not request:
            raise DomainError("ALERT_NOT_FOUND", "Alert request not found")
        if request.status != AlertRequestStatus.PENDING:
            raise DomainError("ALERT_NOT_PENDING", f"Alert is {request.status}")
        if not reason.strip():
            raise DomainError("REASON_REQUIRED", "Rejection reason is required")

        request.reject()
        await self._alerts.save_request(request)

        decision = AlertRequestDecision(
            alert_request_id=request.id,
            decision=AlertDecisionType.REJECT,
            reason=reason.strip(),
            decided_by=agent_id,
            ticket_count_snapshot=request.ticket_count,
        )
        decision = await self._alerts.save_decision(decision)

        await self._audit.append(
            AuditEntry(
                action="alert_request.rejected",
                actor=str(agent_id),
                resource_type="alert_request",
                resource_id=str(request.id),
                details={
                    "reason": reason,
                    "ticket_count": request.ticket_count,
                    "fingerprint": request.fingerprint,
                    "decided_at": decision.decided_at.isoformat(),
                },
            )
        )
        return decision


class ResolveIncident:
    def __init__(
        self,
        incidents: IncidentRepositoryPort,
        audit: AuditRepositoryPort,
    ) -> None:
        self._incidents = incidents
        self._audit = audit

    async def execute(self, *, incident_id: UUID, agent_id: UUID) -> Incident:
        incident = await self._incidents.get_by_id(incident_id)
        if not incident:
            raise DomainError("INCIDENT_NOT_FOUND", "Incident not found")
        incident.resolve()
        incident = await self._incidents.save(incident)
        await self._audit.append(
            AuditEntry(
                action="incident.resolved",
                actor=str(agent_id),
                resource_type="incident",
                resource_id=str(incident.id),
                details={"number": incident.number},
            )
        )
        return incident


class GetAlertDetail:
    def __init__(
        self,
        alerts: AlertRepositoryPort,
        tickets: TicketRepositoryPort,
    ) -> None:
        self._alerts = alerts
        self._tickets = tickets

    async def execute(self, *, alert_id: UUID) -> AlertDetailView:
        request = await self._alerts.get_request(alert_id)
        if not request:
            raise DomainError("ALERT_NOT_FOUND", "Alert request not found")

        tickets = await self._tickets.list_by_ids(request.ticket_ids)
        if not tickets:
            tickets = await self._tickets.list_by_fingerprint(request.fingerprint)

        reason = (
            f"CELU detectó {request.ticket_count} reportes con el mismo fingerprint "
            f"({request.problem_code}) dentro de una ventana de {request.window_seconds}s. "
            "Esto sugiere un incidente sistémico que requiere coordinación de equipos L2/L3 "
            "y consolidar los tickets hijos bajo un ticket padre."
        )
        return AlertDetailView(
            id=request.id,
            fingerprint=request.fingerprint,
            problem_code=request.problem_code,
            ticket_count=request.ticket_count,
            window_seconds=request.window_seconds,
            status=request.status.value,
            public_title=request.public_title,
            created_at=request.created_at,
            reason=reason,
            tickets=[
                AlertTicketDetail(
                    id=t.id,
                    number=t.number,
                    status=t.status.value,
                    priority=t.priority.value,
                    customer_name=f"{t.customer_first_name} {t.customer_last_name}",
                    customer_email=t.customer_email,
                    summary_ai=t.summary_ai,
                    description=t.description,
                    created_at=t.created_at,
                )
                for t in tickets
            ],
        )


class CreateManualIncident:
    """Agente de turno crea alerta/incidente y escala a L2/L3."""

    def __init__(
        self,
        incidents: IncidentRepositoryPort,
        tickets: TicketRepositoryPort,
        audit: AuditRepositoryPort,
    ) -> None:
        self._incidents = incidents
        self._tickets = tickets
        self._audit = audit

    async def execute(
        self,
        *,
        agent_id: UUID,
        title: str,
        problem_code: str,
        public_message: str,
        fingerprint: str | None = None,
        escalation_level: str = "l2",
        link_existing_fingerprint: bool = True,
    ) -> Incident:
        if not title.strip() or not problem_code.strip():
            raise DomainError("INVALID_INPUT", "Título y código de problema son obligatorios")

        fp = (fingerprint or f"manual:{problem_code.strip().lower()}").strip()
        existing = await self._incidents.get_active_by_fingerprint(fp)
        if existing:
            raise DomainError("INCIDENT_EXISTS", f"Ya existe incidente activo {existing.number}")

        level = escalation_level if escalation_level in {"l2", "l3"} else "l2"
        ticket_ids: list[UUID] = []
        if link_existing_fingerprint and not fp.startswith("manual:"):
            related = await self._tickets.list_by_fingerprint(fp)
            ticket_ids = [t.id for t in related]

        seq = await self._incidents.next_sequence()
        number = IncidentNumber.generate(utcnow().year, seq).value
        msg = public_message.strip() or (
            f"Incidente manual {problem_code.upper()}. Equipo {level.upper()} convocado."
        )
        incident = Incident(
            number=number,
            title=f"Ticket padre incidente · {title.strip()} · Escalado {level.upper()}",
            fingerprint=fp,
            problem_code=problem_code.strip().lower(),
            status=IncidentStatus.ACTIVE,
            public_message=msg,
            created_from_alert_id=None,
            created_by=agent_id,
            ticket_ids=ticket_ids,
            escalation_level=level,
            is_parent=True,
        )
        incident = await self._incidents.save(incident)
        if ticket_ids:
            await self._tickets.link_to_incident(ticket_ids, incident.id)

        await self._audit.append(
            AuditEntry(
                action="incident.created_manual",
                actor=str(agent_id),
                resource_type="incident",
                resource_id=str(incident.id),
                details={
                    "escalation_level": level,
                    "problem_code": incident.problem_code,
                    "linked_tickets": len(ticket_ids),
                },
            )
        )
        return incident
