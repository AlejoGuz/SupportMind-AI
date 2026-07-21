from __future__ import annotations

import secrets
from dataclasses import dataclass
from uuid import UUID

from supportmind.application.ports.interfaces import (
    ConversationRepositoryPort,
    DecisionTreeRepositoryPort,
    IncidentRepositoryPort,
    ProductRepositoryPort,
)
from supportmind.domain.common.base import DomainError
from supportmind.domain.common.enums import ConversationOutcome, NodeType
from supportmind.domain.conversation.entities import ConversationSession, DecisionNode


@dataclass
class CurrentNodeView:
    session_id: UUID
    public_token: str
    node_id: UUID
    node_code: str
    prompt: str
    node_type: NodeType
    options: list[dict]
    outcome: ConversationOutcome | None
    blocked_message: str | None = None


class StartChatSession:
    def __init__(
        self,
        trees: DecisionTreeRepositoryPort,
        conversations: ConversationRepositoryPort,
        products: ProductRepositoryPort,
    ) -> None:
        self._trees = trees
        self._conversations = conversations
        self._products = products

    async def execute(self, *, tree_slug: str = "phone-power", product_id: UUID | None = None) -> CurrentNodeView:
        tree = await self._trees.get_active_by_slug(tree_slug)
        if not tree or not tree.root_node_id:
            raise DomainError("TREE_NOT_FOUND", f"Active tree '{tree_slug}' not found")
        if product_id:
            product = await self._products.get_by_id(product_id)
            if not product:
                raise DomainError("PRODUCT_NOT_FOUND", "Product not found")

        root = await self._trees.get_node(tree.root_node_id)
        if not root:
            raise DomainError("NODE_NOT_FOUND", "Root node missing")

        session = ConversationSession(
            public_token=secrets.token_urlsafe(24),
            tree_id=tree.id,
            tree_version=tree.version,
            current_node_id=root.id,
            product_id=product_id,
        )
        session = await self._conversations.save(session)
        return _to_view(session, root)


class AnswerChatStep:
    def __init__(
        self,
        trees: DecisionTreeRepositoryPort,
        conversations: ConversationRepositoryPort,
        incidents: IncidentRepositoryPort,
        products: ProductRepositoryPort,
    ) -> None:
        self._trees = trees
        self._conversations = conversations
        self._incidents = incidents
        self._products = products

    async def execute(self, *, session_id: UUID, option_id: UUID) -> CurrentNodeView:
        session = await self._conversations.get_by_id(session_id)
        if not session:
            raise DomainError("SESSION_NOT_FOUND", "Chat session not found")
        if session.outcome is not None:
            raise DomainError("SESSION_CLOSED", "Session already completed")

        current = await self._trees.get_node(session.current_node_id)
        if not current:
            raise DomainError("NODE_NOT_FOUND", "Current node missing")

        option = next((o for o in current.options if o.id == option_id), None)
        if not option or not option.next_node_id:
            raise DomainError("INVALID_OPTION", "Option not valid for current node")

        next_node = await self._trees.get_node(option.next_node_id)
        if not next_node:
            raise DomainError("NODE_NOT_FOUND", "Next node missing")

        session.record_step(
            node_id=current.id,
            node_code=current.code,
            prompt=current.prompt,
            option_id=option.id,
            option_label=option.label,
            next_node_id=next_node.id,
        )

        blocked_message = None
        if next_node.node_type == NodeType.RESOLVE:
            session.complete(ConversationOutcome.RESOLVED)
        elif next_node.node_type == NodeType.ESCALATE:
            fingerprint_preview = await self._preview_fingerprint(session, next_node)
            active = await self._incidents.get_active_by_fingerprint(fingerprint_preview)
            if active:
                session.complete(ConversationOutcome.BLOCKED_BY_INCIDENT)
                blocked_message = (
                    f"Ya existe un incidente conocido para este inconveniente "
                    f"({active.number}). Nuestro equipo se encuentra trabajando para solucionarlo."
                )

        session = await self._conversations.save(session)
        return _to_view(session, next_node, blocked_message=blocked_message)

    async def _preview_fingerprint(self, session: ConversationSession, leaf: DecisionNode) -> str:
        from supportmind.domain.common.services import FingerprintBuilder

        product_family = "unknown"
        if session.product_id:
            product = await self._products.get_by_id(session.product_id)
            if product:
                product_family = product.family
        path_codes = [s.node_code for s in session.path if s.node_code] + [leaf.code]
        return FingerprintBuilder.build(
            leaf_node_code=leaf.code,
            product_family=product_family,
            path_codes=path_codes,
        ).value


class GetCurrentNode:
    def __init__(
        self,
        trees: DecisionTreeRepositoryPort,
        conversations: ConversationRepositoryPort,
    ) -> None:
        self._trees = trees
        self._conversations = conversations

    async def execute(self, *, session_id: UUID) -> CurrentNodeView:
        session = await self._conversations.get_by_id(session_id)
        if not session:
            raise DomainError("SESSION_NOT_FOUND", "Chat session not found")
        node = await self._trees.get_node(session.current_node_id)
        if not node:
            raise DomainError("NODE_NOT_FOUND", "Current node missing")
        return _to_view(session, node)


def _to_view(
    session: ConversationSession,
    node: DecisionNode,
    blocked_message: str | None = None,
) -> CurrentNodeView:
    return CurrentNodeView(
        session_id=session.id,
        public_token=session.public_token,
        node_id=node.id,
        node_code=node.code,
        prompt=node.prompt if not blocked_message else blocked_message,
        node_type=node.node_type,
        options=(
            []
            if blocked_message or session.outcome is not None
            else [
                {"id": str(o.id), "label": o.label, "sort_order": o.sort_order}
                for o in sorted(node.options, key=lambda x: x.sort_order)
            ]
        ),
        outcome=session.outcome,
        blocked_message=blocked_message,
    )
