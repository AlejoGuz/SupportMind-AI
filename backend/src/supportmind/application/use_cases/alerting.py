from __future__ import annotations

from uuid import UUID

from supportmind.application.ports.interfaces import (
    AlertRepositoryPort,
    AuditRepositoryPort,
    IncidentRepositoryPort,
    TicketRepositoryPort,
)
from supportmind.domain.alerting.entities import AlertRequestDecision, Incident
from supportmind.domain.catalog.entities import AuditEntry
from supportmind.domain.common.base import DomainError, utcnow
from supportmind.domain.common.enums import AlertDecisionType, AlertRequestStatus, IncidentStatus
from supportmind.domain.common.value_objects import IncidentNumber


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

    async def execute(self, *, alert_id: UUID, agent_id: UUID) -> Incident:
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

        seq = await self._incidents.next_sequence()
        number = IncidentNumber.generate(utcnow().year, seq).value
        public_message = (
            f"Actualmente existe un incidente conocido relacionado con {request.problem_code.upper()}. "
            "Nuestro equipo ya está trabajando para resolverlo."
        )
        incident = Incident(
            number=number,
            title=request.public_title or f"Incidente {request.problem_code}",
            fingerprint=request.fingerprint,
            problem_code=request.problem_code,
            status=IncidentStatus.ACTIVE,
            public_message=public_message,
            created_from_alert_id=request.id,
            created_by=agent_id,
            ticket_ids=list(request.ticket_ids),
        )
        incident = await self._incidents.save(incident)
        if request.ticket_ids:
            await self._tickets.link_to_incident(request.ticket_ids, incident.id)

        await self._audit.append(
            AuditEntry(
                action="alert_request.accepted",
                actor=str(agent_id),
                resource_type="incident",
                resource_id=str(incident.id),
                details={
                    "alert_id": str(request.id),
                    "ticket_count": request.ticket_count,
                    "fingerprint": request.fingerprint,
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
