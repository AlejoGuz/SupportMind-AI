from __future__ import annotations
from typing import Optional
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from supportmind.application.use_cases.alerting import AcceptAlertRequest, RejectAlertRequest, ResolveIncident
from supportmind.application.use_cases.auth import LoginAgent
from supportmind.application.use_cases.chat import AnswerChatStep, GetCurrentNode, StartChatSession
from supportmind.application.use_cases.ticketing import EscalateToTicket
from supportmind.config import Settings, get_settings
from supportmind.infrastructure.ai.providers import build_ai_provider
from supportmind.infrastructure.auth.security import parse_agent_id
from supportmind.infrastructure.cache.correlation import RedisCorrelationService
from supportmind.infrastructure.db.session import get_session
from supportmind.infrastructure.repositories.sqlalchemy_repos import (
    SqlAlchemyAgentRepository,
    SqlAlchemyAlertRepository,
    SqlAlchemyAuditRepository,
    SqlAlchemyConversationRepository,
    SqlAlchemyDecisionTreeRepository,
    SqlAlchemyIncidentRepository,
    SqlAlchemyProductRepository,
    SqlAlchemySlaRepository,
    SqlAlchemyTicketRepository,
)
from supportmind.infrastructure.storage.local import LocalObjectStorage


@dataclass
class Container:
    settings: Settings
    session: AsyncSession

    @property
    def agents(self) -> SqlAlchemyAgentRepository:
        return SqlAlchemyAgentRepository(self.session)

    @property
    def products(self) -> SqlAlchemyProductRepository:
        return SqlAlchemyProductRepository(self.session)

    @property
    def trees(self) -> SqlAlchemyDecisionTreeRepository:
        return SqlAlchemyDecisionTreeRepository(self.session)

    @property
    def conversations(self) -> SqlAlchemyConversationRepository:
        return SqlAlchemyConversationRepository(self.session)

    @property
    def tickets(self) -> SqlAlchemyTicketRepository:
        return SqlAlchemyTicketRepository(self.session)

    @property
    def sla(self) -> SqlAlchemySlaRepository:
        return SqlAlchemySlaRepository(self.session)

    @property
    def alerts(self) -> SqlAlchemyAlertRepository:
        return SqlAlchemyAlertRepository(self.session)

    @property
    def incidents(self) -> SqlAlchemyIncidentRepository:
        return SqlAlchemyIncidentRepository(self.session)

    @property
    def audit(self) -> SqlAlchemyAuditRepository:
        return SqlAlchemyAuditRepository(self.session)

    @property
    def correlation(self) -> RedisCorrelationService:
        return RedisCorrelationService()

    @property
    def storage(self) -> LocalObjectStorage:
        return LocalObjectStorage()

    @property
    def ai(self):
        return build_ai_provider(self.settings.ai_provider)


async def get_container(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Container:
    return Container(settings=settings, session=session)


async def get_current_agent_id(authorization: Optional[str] = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        return str(parse_agent_id(token))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def start_chat_uc(c: Container = Depends(get_container)) -> StartChatSession:
    return StartChatSession(c.trees, c.conversations, c.products)


def answer_chat_uc(c: Container = Depends(get_container)) -> AnswerChatStep:
    return AnswerChatStep(c.trees, c.conversations, c.incidents, c.products)


def current_node_uc(c: Container = Depends(get_container)) -> GetCurrentNode:
    return GetCurrentNode(c.trees, c.conversations)


def escalate_uc(c: Container = Depends(get_container)) -> EscalateToTicket:
    return EscalateToTicket(
        conversations=c.conversations,
        trees=c.trees,
        products=c.products,
        tickets=c.tickets,
        agents=c.agents,
        sla=c.sla,
        incidents=c.incidents,
        alerts=c.alerts,
        correlation=c.correlation,
        ai=c.ai,
        audit=c.audit,
    )


def login_uc(c: Container = Depends(get_container)) -> LoginAgent:
    return LoginAgent(c.agents)


def accept_alert_uc(c: Container = Depends(get_container)) -> AcceptAlertRequest:
    return AcceptAlertRequest(c.alerts, c.incidents, c.tickets, c.audit)


def reject_alert_uc(c: Container = Depends(get_container)) -> RejectAlertRequest:
    return RejectAlertRequest(c.alerts, c.audit)


def resolve_incident_uc(c: Container = Depends(get_container)) -> ResolveIncident:
    return ResolveIncident(c.incidents, c.audit)
