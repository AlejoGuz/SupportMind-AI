from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from supportmind.config import get_settings
from supportmind.domain.identity.entities import Agent

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _encode(payload: dict[str, Any], expires_delta: timedelta) -> str:
    settings = get_settings()
    data = payload.copy()
    data["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(data, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_token_pair(agent: Agent) -> dict[str, str]:
    settings = get_settings()
    base = {
        "sub": str(agent.id),
        "email": agent.email,
        "roles": [r.value for r in agent.roles],
        "name": agent.full_name,
    }
    access = _encode(
        {**base, "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh = _encode(
        {**base, "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def refresh_access_token(refresh_token: str) -> dict[str, str]:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise ValueError("Invalid refresh token")
    settings = get_settings()
    access = _encode(
        {
            "sub": payload["sub"],
            "email": payload["email"],
            "roles": payload.get("roles", []),
            "name": payload.get("name", ""),
            "type": "access",
        },
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    return {"access_token": access, "token_type": "bearer"}


def parse_agent_id(token: str) -> UUID:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise ValueError("Invalid access token")
    return UUID(payload["sub"])
