from __future__ import annotations

from supportmind.application.ports.interfaces import AgentRepositoryPort
from supportmind.domain.common.base import DomainError
from supportmind.domain.identity.entities import Agent
from supportmind.infrastructure.auth.security import verify_password, create_token_pair


class LoginAgent:
    def __init__(self, agents: AgentRepositoryPort) -> None:
        self._agents = agents

    async def execute(self, *, email: str, password: str) -> dict:
        agent = await self._agents.get_by_email(email.lower().strip())
        if not agent or not agent.is_active:
            raise DomainError("INVALID_CREDENTIALS", "Invalid email or password")
        if not verify_password(password, agent.hashed_password):
            raise DomainError("INVALID_CREDENTIALS", "Invalid email or password")
        tokens = create_token_pair(agent)
        return {"agent": agent, "tokens": tokens}
