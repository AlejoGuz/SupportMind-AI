from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from supportmind.config import get_settings
from supportmind.domain.common.base import DomainError
from supportmind.presentation.api.v1 import agent, public


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="SupportMind AI — intelligent ITSM with CELU guided chatbot",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError):
        return JSONResponse(
            status_code=400,
            content={
                "type": "about:blank",
                "title": exc.code,
                "status": 400,
                "detail": exc.message,
                "code": exc.code,
                "details": exc.details,
            },
        )

    app.include_router(public.router, prefix=settings.api_prefix)
    app.include_router(agent.router, prefix=settings.api_prefix)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": settings.app_name}

    @app.get("/ready")
    async def ready():
        return {"status": "ready"}

    return app


app = create_app()
