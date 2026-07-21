from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from supportmind.domain.alerting.entities import AlertRequest, AlertRequestDecision, Incident
from supportmind.domain.catalog.entities import AuditEntry, Product
from supportmind.domain.common.enums import (
    AgentAvailability,
    AgentRole,
    AlertDecisionType,
    AlertRequestStatus,
    Channel,
    ConversationOutcome,
    IncidentStatus,
    NodeType,
    Priority,
    Sentiment,
    TicketStatus,
)
from supportmind.domain.conversation.entities import (
    ConversationSession,
    ConversationStep,
    DecisionNode,
    DecisionOption,
    DecisionTree,
)
from supportmind.domain.identity.entities import Agent
from supportmind.domain.sla.entities import SlaPolicy, TicketSlaClock
from supportmind.domain.ticketing.entities import Ticket, TicketAttachment, TicketEvent
from supportmind.infrastructure.db import models as m


def _dt(value: datetime | None) -> datetime | None:
    return value


class SqlAlchemyAgentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, row: m.AgentModel) -> Agent:
        return Agent(
            id=row.id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            email=row.email,
            full_name=row.full_name,
            hashed_password=row.hashed_password,
            roles=[AgentRole(r) for r in (row.roles or [])],
            availability=AgentAvailability(row.availability),
            is_active=row.is_active,
            open_ticket_count=row.open_ticket_count,
        )

    async def get_by_email(self, email: str) -> Agent | None:
        result = await self._session.execute(select(m.AgentModel).where(m.AgentModel.email == email))
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def get_by_id(self, agent_id: UUID) -> Agent | None:
        row = await self._session.get(m.AgentModel, agent_id)
        return self._to_entity(row) if row else None

    async def list_agents(self) -> list[Agent]:
        result = await self._session.execute(select(m.AgentModel).order_by(m.AgentModel.full_name))
        return [self._to_entity(r) for r in result.scalars().all()]

    async def list_available_l1(self) -> list[Agent]:
        result = await self._session.execute(select(m.AgentModel).where(m.AgentModel.is_active.is_(True)))
        agents = [self._to_entity(r) for r in result.scalars().all()]
        return [a for a in agents if a.is_l1_available()]

    async def save(self, agent: Agent) -> Agent:
        row = await self._session.get(m.AgentModel, agent.id)
        if not row:
            row = m.AgentModel(id=agent.id)
            self._session.add(row)
        row.email = agent.email
        row.full_name = agent.full_name
        row.hashed_password = agent.hashed_password
        row.roles = [r.value for r in agent.roles]
        row.availability = agent.availability.value
        row.is_active = agent.is_active
        row.open_ticket_count = agent.open_ticket_count
        await self._session.flush()
        return agent

    async def increment_open_count(self, agent_id: UUID) -> None:
        await self._session.execute(
            update(m.AgentModel)
            .where(m.AgentModel.id == agent_id)
            .values(open_ticket_count=m.AgentModel.open_ticket_count + 1)
        )


class SqlAlchemyProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, row: m.ProductModel) -> Product:
        return Product(
            id=row.id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            sku=row.sku,
            name=row.name,
            family=row.family,
            brand=row.brand,
            is_active=row.is_active,
        )

    async def list_active(self) -> list[Product]:
        result = await self._session.execute(
            select(m.ProductModel).where(m.ProductModel.is_active.is_(True)).order_by(m.ProductModel.name)
        )
        return [self._to_entity(r) for r in result.scalars().all()]

    async def get_by_id(self, product_id: UUID) -> Product | None:
        row = await self._session.get(m.ProductModel, product_id)
        return self._to_entity(row) if row else None


class SqlAlchemyDecisionTreeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _tree_entity(self, row: m.DecisionTreeModel) -> DecisionTree:
        return DecisionTree(
            id=row.id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            slug=row.slug,
            name=row.name,
            version=row.version,
            is_active=row.is_active,
            root_node_id=row.root_node_id,
            description=row.description or "",
        )

    def _node_entity(self, row: m.DecisionNodeModel) -> DecisionNode:
        options = [
            DecisionOption(
                id=o.id,
                label=o.label,
                next_node_id=o.next_node_id,
                sort_order=o.sort_order,
                metadata=o.metadata_json or {},
            )
            for o in (row.options or [])
        ]
        return DecisionNode(
            id=row.id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            tree_id=row.tree_id,
            code=row.code,
            prompt=row.prompt,
            node_type=NodeType(row.node_type),
            options=options,
            metadata=row.metadata_json or {},
        )

    async def get_active_by_slug(self, slug: str) -> DecisionTree | None:
        result = await self._session.execute(
            select(m.DecisionTreeModel).where(
                m.DecisionTreeModel.slug == slug,
                m.DecisionTreeModel.is_active.is_(True),
            )
        )
        row = result.scalar_one_or_none()
        return self._tree_entity(row) if row else None

    async def get_tree(self, tree_id: UUID) -> DecisionTree | None:
        row = await self._session.get(m.DecisionTreeModel, tree_id)
        return self._tree_entity(row) if row else None

    async def get_node(self, node_id: UUID) -> DecisionNode | None:
        result = await self._session.execute(
            select(m.DecisionNodeModel)
            .options(selectinload(m.DecisionNodeModel.options))
            .where(m.DecisionNodeModel.id == node_id)
        )
        row = result.scalar_one_or_none()
        return self._node_entity(row) if row else None

    async def list_trees(self) -> list[DecisionTree]:
        result = await self._session.execute(select(m.DecisionTreeModel))
        return [self._tree_entity(r) for r in result.scalars().all()]

    async def save_tree(self, tree: DecisionTree) -> DecisionTree:
        row = await self._session.get(m.DecisionTreeModel, tree.id)
        if not row:
            row = m.DecisionTreeModel(id=tree.id)
            self._session.add(row)
        row.slug = tree.slug
        row.name = tree.name
        row.version = tree.version
        row.is_active = tree.is_active
        row.root_node_id = tree.root_node_id
        row.description = tree.description
        await self._session.flush()
        return tree


class SqlAlchemyConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, row: m.ConversationSessionModel) -> ConversationSession:
        path = [
            ConversationStep(
                node_id=UUID(s["node_id"]),
                node_code=s.get("node_code", ""),
                option_id=UUID(s["option_id"]) if s.get("option_id") else None,
                option_label=s.get("option_label"),
                prompt=s.get("prompt", ""),
            )
            for s in (row.path_json or [])
        ]
        return ConversationSession(
            id=row.id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            public_token=row.public_token,
            tree_id=row.tree_id,
            tree_version=row.tree_version,
            current_node_id=row.current_node_id,
            path=path,
            outcome=ConversationOutcome(row.outcome) if row.outcome else None,
            product_id=row.product_id,
            ended_at=row.ended_at,
        )

    async def save(self, session: ConversationSession) -> ConversationSession:
        row = await self._session.get(m.ConversationSessionModel, session.id)
        if not row:
            row = m.ConversationSessionModel(id=session.id)
            self._session.add(row)
        row.public_token = session.public_token
        row.tree_id = session.tree_id
        row.tree_version = session.tree_version
        row.current_node_id = session.current_node_id
        row.path_json = [
            {
                "node_id": str(s.node_id),
                "node_code": s.node_code,
                "option_id": str(s.option_id) if s.option_id else None,
                "option_label": s.option_label,
                "prompt": s.prompt,
            }
            for s in session.path
        ]
        row.outcome = session.outcome.value if session.outcome else None
        row.product_id = session.product_id
        row.ended_at = session.ended_at
        await self._session.flush()
        return session

    async def get_by_id(self, session_id: UUID) -> ConversationSession | None:
        row = await self._session.get(m.ConversationSessionModel, session_id)
        return self._to_entity(row) if row else None

    async def get_by_token(self, token: str) -> ConversationSession | None:
        result = await self._session.execute(
            select(m.ConversationSessionModel).where(m.ConversationSessionModel.public_token == token)
        )
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None


class SqlAlchemyTicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, row: m.TicketModel) -> Ticket:
        attachments = [
            TicketAttachment(
                id=UUID(a["id"]),
                filename=a["filename"],
                content_type=a["content_type"],
                size_bytes=a["size_bytes"],
                storage_key=a["storage_key"],
                created_at=datetime.fromisoformat(a["created_at"]) if a.get("created_at") else datetime.now(timezone.utc),
            )
            for a in (row.attachments_json or [])
        ]
        events = [
            TicketEvent(
                id=UUID(e["id"]),
                event_type=e["event_type"],
                message=e["message"],
                actor=e["actor"],
                payload=e.get("payload") or {},
                created_at=datetime.fromisoformat(e["created_at"]) if e.get("created_at") else datetime.now(timezone.utc),
            )
            for e in (row.events_json or [])
        ]
        return Ticket(
            id=row.id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            number=row.number,
            status=TicketStatus(row.status),
            priority=Priority(row.priority),
            category=row.category,
            sentiment=Sentiment(row.sentiment),
            summary_ai=row.summary_ai,
            customer_first_name=row.customer_first_name,
            customer_last_name=row.customer_last_name,
            customer_email=row.customer_email,
            customer_phone=row.customer_phone,
            order_number=row.order_number,
            product_id=row.product_id,
            description=row.description,
            channel=Channel(row.channel),
            created_by=row.created_by,
            problem_fingerprint=row.problem_fingerprint,
            conversation_session_id=row.conversation_session_id,
            assignee_id=row.assignee_id,
            incident_id=row.incident_id,
            attachments=attachments,
            events=events,
            conversation_transcript=row.conversation_transcript or [],
        )

    def _serialize(self, ticket: Ticket) -> None:
        pass

    async def save(self, ticket: Ticket) -> Ticket:
        row = await self._session.get(m.TicketModel, ticket.id)
        if not row:
            row = m.TicketModel(id=ticket.id)
            self._session.add(row)
        row.number = ticket.number
        row.status = ticket.status.value
        row.priority = ticket.priority.value
        row.category = ticket.category
        row.sentiment = ticket.sentiment.value
        row.summary_ai = ticket.summary_ai
        row.customer_first_name = ticket.customer_first_name
        row.customer_last_name = ticket.customer_last_name
        row.customer_email = ticket.customer_email
        row.customer_phone = ticket.customer_phone
        row.order_number = ticket.order_number
        row.product_id = ticket.product_id
        row.description = ticket.description
        row.channel = ticket.channel.value
        row.created_by = ticket.created_by
        row.assignee_id = ticket.assignee_id
        row.conversation_session_id = ticket.conversation_session_id
        row.problem_fingerprint = ticket.problem_fingerprint
        row.incident_id = ticket.incident_id
        row.conversation_transcript = ticket.conversation_transcript
        row.attachments_json = [
            {
                "id": str(a.id),
                "filename": a.filename,
                "content_type": a.content_type,
                "size_bytes": a.size_bytes,
                "storage_key": a.storage_key,
                "created_at": a.created_at.isoformat(),
            }
            for a in ticket.attachments
        ]
        row.events_json = [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "message": e.message,
                "actor": e.actor,
                "payload": e.payload,
                "created_at": e.created_at.isoformat(),
            }
            for e in ticket.events
        ]
        await self._session.flush()
        return ticket

    async def get_by_id(self, ticket_id: UUID) -> Ticket | None:
        row = await self._session.get(m.TicketModel, ticket_id)
        return self._to_entity(row) if row else None

    async def get_by_number(self, number: str) -> Ticket | None:
        result = await self._session.execute(select(m.TicketModel).where(m.TicketModel.number == number))
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def list_tickets(
        self,
        *,
        status: str | None = None,
        assignee_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Ticket]:
        stmt = select(m.TicketModel).order_by(m.TicketModel.created_at.desc()).limit(limit).offset(offset)
        if status:
            stmt = stmt.where(m.TicketModel.status == status)
        if assignee_id:
            stmt = stmt.where(m.TicketModel.assignee_id == assignee_id)
        result = await self._session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars().all()]

    async def list_by_fingerprint_since(self, fingerprint: str, since_iso_window_seconds: int) -> list[Ticket]:
        since = datetime.now(timezone.utc) - timedelta(seconds=since_iso_window_seconds)
        result = await self._session.execute(
            select(m.TicketModel).where(
                m.TicketModel.problem_fingerprint == fingerprint,
                m.TicketModel.created_at >= since,
            )
        )
        return [self._to_entity(r) for r in result.scalars().all()]

    async def next_sequence(self) -> int:
        year = datetime.now(timezone.utc).year
        result = await self._session.execute(
            select(m.TicketSequenceModel).where(m.TicketSequenceModel.year == year)
        )
        row = result.scalar_one_or_none()
        if not row:
            row = m.TicketSequenceModel(year=year, last_value=0)
            self._session.add(row)
            await self._session.flush()
        row.last_value += 1
        await self._session.flush()
        return row.last_value

    async def link_to_incident(self, ticket_ids: list[UUID], incident_id: UUID) -> None:
        if not ticket_ids:
            return
        await self._session.execute(
            update(m.TicketModel)
            .where(m.TicketModel.id.in_(ticket_ids))
            .values(incident_id=incident_id)
        )


class SqlAlchemySlaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_policy(self, priority: Priority) -> SlaPolicy | None:
        result = await self._session.execute(
            select(m.SlaPolicyModel).where(m.SlaPolicyModel.priority == priority.value)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return SlaPolicy(
            id=row.id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            priority=Priority(row.priority),
            response_minutes=row.response_minutes,
            resolution_minutes=row.resolution_minutes,
            is_active=row.is_active,
        )

    async def list_policies(self) -> list[SlaPolicy]:
        result = await self._session.execute(select(m.SlaPolicyModel))
        return [
            SlaPolicy(
                id=r.id,
                created_at=r.created_at,
                updated_at=r.updated_at,
                priority=Priority(r.priority),
                response_minutes=r.response_minutes,
                resolution_minutes=r.resolution_minutes,
                is_active=r.is_active,
            )
            for r in result.scalars().all()
        ]

    async def save_clock(self, clock: TicketSlaClock) -> TicketSlaClock:
        row = await self._session.get(m.TicketSlaClockModel, clock.id)
        if not row:
            existing = await self._session.execute(
                select(m.TicketSlaClockModel).where(m.TicketSlaClockModel.ticket_id == clock.ticket_id)
            )
            row = existing.scalar_one_or_none()
            if not row:
                row = m.TicketSlaClockModel(id=clock.id)
                self._session.add(row)
        row.ticket_id = clock.ticket_id
        row.priority = clock.priority.value
        row.response_due_at = clock.response_due_at
        row.resolution_due_at = clock.resolution_due_at
        row.response_breached = clock.response_breached
        row.resolution_breached = clock.resolution_breached
        await self._session.flush()
        return clock

    async def get_clock(self, ticket_id: UUID) -> TicketSlaClock | None:
        result = await self._session.execute(
            select(m.TicketSlaClockModel).where(m.TicketSlaClockModel.ticket_id == ticket_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return TicketSlaClock(
            id=row.id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            ticket_id=row.ticket_id,
            priority=Priority(row.priority),
            response_due_at=row.response_due_at,
            resolution_due_at=row.resolution_due_at,
            response_breached=row.response_breached,
            resolution_breached=row.resolution_breached,
        )


class SqlAlchemyAlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, row: m.AlertRequestModel) -> AlertRequest:
        return AlertRequest(
            id=row.id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            fingerprint=row.fingerprint,
            problem_code=row.problem_code,
            ticket_count=row.ticket_count,
            window_seconds=row.window_seconds,
            status=AlertRequestStatus(row.status),
            ticket_ids=[UUID(t) if isinstance(t, str) else t for t in (row.ticket_ids or [])],
            public_title=row.public_title or "",
        )

    async def save_request(self, request: AlertRequest) -> AlertRequest:
        row = await self._session.get(m.AlertRequestModel, request.id)
        if not row:
            row = m.AlertRequestModel(id=request.id)
            self._session.add(row)
        row.fingerprint = request.fingerprint
        row.problem_code = request.problem_code
        row.ticket_count = request.ticket_count
        row.window_seconds = request.window_seconds
        row.status = request.status.value
        row.ticket_ids = [str(t) for t in request.ticket_ids]
        row.public_title = request.public_title
        await self._session.flush()
        return request

    async def get_request(self, request_id: UUID) -> AlertRequest | None:
        row = await self._session.get(m.AlertRequestModel, request_id)
        return self._to_entity(row) if row else None

    async def list_pending(self) -> list[AlertRequest]:
        result = await self._session.execute(
            select(m.AlertRequestModel)
            .where(m.AlertRequestModel.status == AlertRequestStatus.PENDING.value)
            .order_by(m.AlertRequestModel.created_at.desc())
        )
        return [self._to_entity(r) for r in result.scalars().all()]

    async def get_pending_by_fingerprint(self, fingerprint: str) -> AlertRequest | None:
        result = await self._session.execute(
            select(m.AlertRequestModel).where(
                m.AlertRequestModel.fingerprint == fingerprint,
                m.AlertRequestModel.status == AlertRequestStatus.PENDING.value,
            )
        )
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def save_decision(self, decision: AlertRequestDecision) -> AlertRequestDecision:
        row = m.AlertRequestDecisionModel(
            id=decision.id,
            alert_request_id=decision.alert_request_id,
            decision=decision.decision.value,
            reason=decision.reason,
            decided_by=decision.decided_by,
            ticket_count_snapshot=decision.ticket_count_snapshot,
            decided_at=decision.decided_at,
        )
        self._session.add(row)
        await self._session.flush()
        return decision


class SqlAlchemyIncidentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, row: m.IncidentModel) -> Incident:
        return Incident(
            id=row.id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            number=row.number,
            title=row.title,
            fingerprint=row.fingerprint,
            problem_code=row.problem_code,
            status=IncidentStatus(row.status),
            public_message=row.public_message,
            created_from_alert_id=row.created_from_alert_id,
            created_by=row.created_by,
            ticket_ids=[UUID(t) if isinstance(t, str) else t for t in (row.ticket_ids or [])],
            resolved_at=row.resolved_at,
        )

    async def save(self, incident: Incident) -> Incident:
        row = await self._session.get(m.IncidentModel, incident.id)
        if not row:
            row = m.IncidentModel(id=incident.id)
            self._session.add(row)
        row.number = incident.number
        row.title = incident.title
        row.fingerprint = incident.fingerprint
        row.problem_code = incident.problem_code
        row.status = incident.status.value
        row.public_message = incident.public_message
        row.created_from_alert_id = incident.created_from_alert_id
        row.created_by = incident.created_by
        row.ticket_ids = [str(t) for t in incident.ticket_ids]
        row.resolved_at = incident.resolved_at
        await self._session.flush()
        return incident

    async def get_by_id(self, incident_id: UUID) -> Incident | None:
        row = await self._session.get(m.IncidentModel, incident_id)
        return self._to_entity(row) if row else None

    async def get_active_by_fingerprint(self, fingerprint: str) -> Incident | None:
        result = await self._session.execute(
            select(m.IncidentModel).where(
                m.IncidentModel.fingerprint == fingerprint,
                m.IncidentModel.status == IncidentStatus.ACTIVE.value,
            )
        )
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def list_incidents(self, *, status: str | None = None) -> list[Incident]:
        stmt = select(m.IncidentModel).order_by(m.IncidentModel.created_at.desc())
        if status:
            stmt = stmt.where(m.IncidentModel.status == status)
        result = await self._session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars().all()]

    async def list_active_public(self) -> list[Incident]:
        return await self.list_incidents(status=IncidentStatus.ACTIVE.value)

    async def next_sequence(self) -> int:
        year = datetime.now(timezone.utc).year
        result = await self._session.execute(
            select(m.IncidentSequenceModel).where(m.IncidentSequenceModel.year == year)
        )
        row = result.scalar_one_or_none()
        if not row:
            row = m.IncidentSequenceModel(year=year, last_value=0)
            self._session.add(row)
            await self._session.flush()
        row.last_value += 1
        await self._session.flush()
        return row.last_value


class SqlAlchemyAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, entry: AuditEntry) -> AuditEntry:
        row = m.AuditLogModel(
            id=entry.id,
            action=entry.action,
            actor=entry.actor,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            details=entry.details,
        )
        self._session.add(row)
        await self._session.flush()
        return entry

    async def list_recent(self, *, limit: int = 100) -> list[AuditEntry]:
        result = await self._session.execute(
            select(m.AuditLogModel).order_by(m.AuditLogModel.created_at.desc()).limit(limit)
        )
        return [
            AuditEntry(
                id=r.id,
                created_at=r.created_at,
                updated_at=r.updated_at,
                action=r.action,
                actor=r.actor,
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                details=r.details or {},
            )
            for r in result.scalars().all()
        ]
