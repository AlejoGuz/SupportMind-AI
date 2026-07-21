from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from supportmind.application.ports.interfaces import (
    AIProviderPort,
    AgentRepositoryPort,
    AlertRepositoryPort,
    AuditRepositoryPort,
    ConversationRepositoryPort,
    CorrelationPort,
    DecisionTreeRepositoryPort,
    IncidentRepositoryPort,
    ObjectStoragePort,
    ProductRepositoryPort,
    SlaRepositoryPort,
    TicketRepositoryPort,
)
from supportmind.domain.alerting.entities import AlertRequest
from supportmind.domain.catalog.entities import AuditEntry
from supportmind.domain.common.base import DomainError, utcnow
from supportmind.domain.common.enums import (
    AlertRequestStatus,
    Channel,
    ConversationOutcome,
    NodeType,
    TicketStatus,
)
from supportmind.domain.common.services import (
    AgentAssignmentPolicy,
    CategoryClassifier,
    FingerprintBuilder,
    IncidentCorrelationPolicy,
    PriorityCalculator,
    SentimentEstimator,
)
from supportmind.domain.common.value_objects import TicketNumber
from supportmind.domain.sla.entities import TicketSlaClock
from supportmind.domain.ticketing.entities import Ticket, TicketAttachment, TicketEvent
from supportmind.config import get_settings


@dataclass
class EscalateInput:
    session_id: UUID
    first_name: str
    last_name: str
    email: str
    phone: str
    order_number: str
    product_id: UUID
    description: str
    attachment_keys: list[dict[str, Any]] | None = None


class EscalateToTicket:
    def __init__(
        self,
        conversations: ConversationRepositoryPort,
        trees: DecisionTreeRepositoryPort,
        products: ProductRepositoryPort,
        tickets: TicketRepositoryPort,
        agents: AgentRepositoryPort,
        sla: SlaRepositoryPort,
        incidents: IncidentRepositoryPort,
        alerts: AlertRepositoryPort,
        correlation: CorrelationPort,
        ai: AIProviderPort,
        audit: AuditRepositoryPort,
        assignment: AgentAssignmentPolicy | None = None,
        correlation_policy: IncidentCorrelationPolicy | None = None,
    ) -> None:
        self._conversations = conversations
        self._trees = trees
        self._products = products
        self._tickets = tickets
        self._agents = agents
        self._sla = sla
        self._incidents = incidents
        self._alerts = alerts
        self._correlation = correlation
        self._ai = ai
        self._audit = audit
        self._assignment = assignment or AgentAssignmentPolicy()
        settings = get_settings()
        self._corr_policy = correlation_policy or IncidentCorrelationPolicy(
            threshold=settings.correlation_threshold,
            window_seconds=settings.correlation_window_seconds,
        )

    async def execute(self, data: EscalateInput) -> Ticket:
        session = await self._conversations.get_by_id(data.session_id)
        if not session:
            raise DomainError("SESSION_NOT_FOUND", "Chat session not found")
        if session.outcome == ConversationOutcome.BLOCKED_BY_INCIDENT:
            raise DomainError("BLOCKED_BY_INCIDENT", "Active incident already covers this issue")
        if session.outcome == ConversationOutcome.ESCALATED:
            raise DomainError("ALREADY_ESCALATED", "Session already created a ticket")

        current = await self._trees.get_node(session.current_node_id)
        if not current or current.node_type != NodeType.ESCALATE:
            raise DomainError("NOT_ESCALATION_NODE", "Session is not ready to escalate")

        product = await self._products.get_by_id(data.product_id)
        if not product:
            raise DomainError("PRODUCT_NOT_FOUND", "Product not found")

        path_codes = [s.node_code for s in session.path if s.node_code] + [current.code]
        fingerprint = FingerprintBuilder.build(
            leaf_node_code=current.code,
            product_family=product.family,
            path_codes=path_codes,
        ).value

        active = await self._incidents.get_active_by_fingerprint(fingerprint)
        if active:
            session.complete(ConversationOutcome.BLOCKED_BY_INCIDENT)
            await self._conversations.save(session)
            raise DomainError(
                "BLOCKED_BY_INCIDENT",
                f"Ya existe un incidente conocido ({active.number}). No se generará un ticket duplicado.",
                {"incident_number": active.number},
            )

        transcript = [
            {
                "prompt": s.prompt,
                "answer": s.option_label,
                "node_code": s.node_code,
            }
            for s in session.path
        ]

        enrichment = await self._ai.enrich_ticket(
            description=data.description,
            leaf_code=current.code,
            path_codes=path_codes,
            product_name=product.name,
            transcript=transcript,
        )

        # Fallbacks if AI returns nothing unexpected
        priority = enrichment.priority or PriorityCalculator().calculate(
            leaf_code=current.code, path_codes=path_codes
        )
        category = enrichment.category or CategoryClassifier().classify(
            leaf_code=current.code, path_codes=path_codes
        )
        sentiment = enrichment.sentiment or SentimentEstimator().estimate(
            leaf_code=current.code, path_codes=path_codes
        )

        seq = await self._tickets.next_sequence()
        number = TicketNumber.generate(utcnow().year, seq).value

        l1 = self._assignment.choose(await self._agents.list_available_l1())
        attachments = []
        for att in data.attachment_keys or []:
            attachments.append(
                TicketAttachment(
                    id=uuid4(),
                    filename=att["filename"],
                    content_type=att.get("content_type", "application/octet-stream"),
                    size_bytes=att.get("size_bytes", 0),
                    storage_key=att["storage_key"],
                )
            )

        ticket = Ticket(
            number=number,
            status=TicketStatus.NEW,
            priority=priority,
            category=category,
            sentiment=sentiment,
            summary_ai=enrichment.summary,
            customer_first_name=data.first_name,
            customer_last_name=data.last_name,
            customer_email=data.email,
            customer_phone=data.phone,
            order_number=data.order_number,
            product_id=product.id,
            description=data.description,
            channel=Channel.CELU_CHAT,
            created_by="CELU_BOT",
            problem_fingerprint=fingerprint,
            conversation_session_id=session.id,
            attachments=attachments,
            conversation_transcript=transcript,
            events=[
                TicketEvent(
                    id=uuid4(),
                    event_type="created",
                    message="Ticket creado automáticamente por CELU",
                    actor="CELU_BOT",
                    payload={"fingerprint": fingerprint, "provider": enrichment.provider},
                )
            ],
        )

        if l1:
            ticket.assign(l1.id)
            ticket.events.append(
                TicketEvent(
                    id=uuid4(),
                    event_type="assigned",
                    message=f"Asignado a {l1.full_name}",
                    actor="system",
                    payload={"assignee_id": str(l1.id)},
                )
            )

        ticket = await self._tickets.save(ticket)
        if l1:
            await self._agents.increment_open_count(l1.id)

        policy = await self._sla.get_policy(priority)
        if policy:
            clock = TicketSlaClock.start(ticket.id, policy)
            await self._sla.save_clock(clock)

        session.product_id = product.id
        session.complete(ConversationOutcome.ESCALATED)
        await self._conversations.save(session)

        await self._audit.append(
            AuditEntry(
                action="ticket.created",
                actor="CELU_BOT",
                resource_type="ticket",
                resource_id=str(ticket.id),
                details={"number": ticket.number, "fingerprint": fingerprint},
            )
        )

        settings = get_settings()
        count = await self._correlation.record_and_count(
            fingerprint, ticket.id, settings.correlation_window_seconds
        )
        if self._corr_policy.should_request_alert(count):
            await self._maybe_create_alert_request(fingerprint, current.code, count)

        return ticket

    async def _maybe_create_alert_request(
        self, fingerprint: str, problem_code: str, count: int
    ) -> None:
        settings = get_settings()
        existing = await self._alerts.get_pending_by_fingerprint(fingerprint)
        if existing:
            return
        locked = await self._correlation.try_acquire_alert_lock(
            fingerprint, settings.correlation_window_seconds * 2
        )
        if not locked:
            return
        related = await self._tickets.list_by_fingerprint_since(
            fingerprint, settings.correlation_window_seconds
        )
        request = AlertRequest(
            fingerprint=fingerprint,
            problem_code=problem_code,
            ticket_count=max(count, len(related)),
            window_seconds=settings.correlation_window_seconds,
            status=AlertRequestStatus.PENDING,
            ticket_ids=[t.id for t in related],
            public_title=f"CELU detectó múltiples reportes del error {problem_code.upper()}.",
        )
        await self._alerts.save_request(request)
        await self._audit.append(
            AuditEntry(
                action="alert_request.created",
                actor="CELU_BOT",
                resource_type="alert_request",
                resource_id=str(request.id),
                details={
                    "fingerprint": fingerprint,
                    "ticket_count": request.ticket_count,
                    "problem_code": problem_code,
                },
            )
        )
