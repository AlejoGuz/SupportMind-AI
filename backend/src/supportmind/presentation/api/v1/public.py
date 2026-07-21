from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from supportmind.application.use_cases.chat import AnswerChatStep, GetCurrentNode, StartChatSession
from supportmind.application.use_cases.ticketing import EscalateInput, EscalateToTicket
from supportmind.dependencies import (
    answer_chat_uc,
    current_node_uc,
    escalate_uc,
    get_container,
    start_chat_uc,
    Container,
)
from supportmind.domain.common.base import DomainError
from supportmind.domain.ticketing.entities import Ticket
from supportmind.presentation.schemas.api import (
    AnswerRequest,
    CurrentNodeResponse,
    EscalateRequest,
    OptionOut,
    ProductOut,
    StartSessionRequest,
    TicketOut,
)

router = APIRouter(tags=["public"])


def _domain_http(exc: DomainError) -> HTTPException:
    code_map = {
        "INVALID_CREDENTIALS": 401,
        "SESSION_NOT_FOUND": 404,
        "TREE_NOT_FOUND": 404,
        "PRODUCT_NOT_FOUND": 404,
        "BLOCKED_BY_INCIDENT": 409,
        "ALREADY_ESCALATED": 409,
    }
    return HTTPException(
        status_code=code_map.get(exc.code, 400),
        detail={"code": exc.code, "message": exc.message, "details": exc.details},
    )


def _ticket_out(ticket: Ticket, sla_remaining: int | None = None) -> TicketOut:
    return TicketOut(
        id=ticket.id,
        number=ticket.number,
        status=ticket.status.value,
        priority=ticket.priority.value,
        category=ticket.category,
        sentiment=ticket.sentiment.value,
        summary_ai=ticket.summary_ai,
        customer_first_name=ticket.customer_first_name,
        customer_last_name=ticket.customer_last_name,
        customer_email=ticket.customer_email,
        customer_phone=ticket.customer_phone,
        order_number=ticket.order_number,
        product_id=ticket.product_id,
        description=ticket.description,
        channel=ticket.channel.value,
        created_by=ticket.created_by,
        assignee_id=ticket.assignee_id,
        incident_id=ticket.incident_id,
        problem_fingerprint=ticket.problem_fingerprint,
        conversation_transcript=ticket.conversation_transcript,
        attachments=[
            {
                "id": str(a.id),
                "filename": a.filename,
                "content_type": a.content_type,
                "size_bytes": a.size_bytes,
                "storage_key": a.storage_key,
            }
            for a in ticket.attachments
        ],
        events=[
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "message": e.message,
                "actor": e.actor,
                "payload": e.payload,
                "created_at": e.created_at.isoformat(),
            }
            for e in ticket.events
        ],
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        sla_remaining_seconds=sla_remaining,
    )


def _node_out(view) -> CurrentNodeResponse:
    return CurrentNodeResponse(
        session_id=view.session_id,
        public_token=view.public_token,
        node_id=view.node_id,
        node_code=view.node_code,
        prompt=view.prompt,
        node_type=view.node_type.value,
        options=[OptionOut(**o) for o in view.options],
        outcome=view.outcome.value if view.outcome else None,
        blocked_message=view.blocked_message,
    )


@router.post("/chat/sessions", response_model=CurrentNodeResponse)
async def start_session(
    body: StartSessionRequest,
    uc: StartChatSession = Depends(start_chat_uc),
):
    try:
        view = await uc.execute(tree_slug=body.tree_slug, product_id=body.product_id)
        return _node_out(view)
    except DomainError as exc:
        raise _domain_http(exc) from exc


@router.get("/chat/sessions/{session_id}/current", response_model=CurrentNodeResponse)
async def current_node(
    session_id: UUID,
    uc: GetCurrentNode = Depends(current_node_uc),
):
    try:
        view = await uc.execute(session_id=session_id)
        return _node_out(view)
    except DomainError as exc:
        raise _domain_http(exc) from exc


@router.post("/chat/sessions/{session_id}/answers", response_model=CurrentNodeResponse)
async def answer(
    session_id: UUID,
    body: AnswerRequest,
    uc: AnswerChatStep = Depends(answer_chat_uc),
):
    try:
        view = await uc.execute(session_id=session_id, option_id=body.option_id)
        return _node_out(view)
    except DomainError as exc:
        raise _domain_http(exc) from exc


@router.post("/chat/sessions/{session_id}/escalate", response_model=TicketOut)
async def escalate(
    session_id: UUID,
    body: EscalateRequest,
    uc: EscalateToTicket = Depends(escalate_uc),
):
    try:
        ticket = await uc.execute(
            EscalateInput(
                session_id=session_id,
                first_name=body.first_name,
                last_name=body.last_name,
                email=str(body.email),
                phone=body.phone,
                order_number=body.order_number,
                product_id=body.product_id,
                description=body.description,
                attachment_keys=body.attachment_keys,
            )
        )
        return _ticket_out(ticket)
    except DomainError as exc:
        raise _domain_http(exc) from exc


@router.post("/chat/attachments")
async def upload_attachment(
    file: UploadFile = File(...),
    c: Container = Depends(get_container),
):
    data = await file.read()
    key = await c.storage.upload(
        bucket=c.settings.s3_bucket_attachments,
        key=f"{uuid4().hex}_{file.filename}",
        data=data,
        content_type=file.content_type or "application/octet-stream",
    )
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(data),
        "storage_key": key,
    }


@router.get("/catalog/products", response_model=list[ProductOut])
async def list_products(c: Container = Depends(get_container)):
    products = await c.products.list_active()
    return [
        ProductOut(id=p.id, sku=p.sku, name=p.name, family=p.family, brand=p.brand) for p in products
    ]


@router.get("/public/incidents/active")
async def active_incidents(c: Container = Depends(get_container)):
    incidents = await c.incidents.list_active_public()
    return [
        {
            "id": str(i.id),
            "number": i.number,
            "problem_code": i.problem_code,
            "public_message": i.public_message,
            "title": i.title,
        }
        for i in incidents
    ]
