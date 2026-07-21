from __future__ import annotations

import time
from uuid import UUID

from redis.asyncio import Redis

from supportmind.config import get_settings


class RedisCorrelationService:
    def __init__(self, redis: Redis | None = None) -> None:
        self._redis = redis
        self._memory: dict[str, list[tuple[float, str]]] = {}
        self._locks: dict[str, float] = {}

    async def _client(self) -> Redis | None:
        if self._redis is not None:
            return self._redis
        try:
            client = Redis.from_url(get_settings().redis_url, decode_responses=True)
            await client.ping()
            self._redis = client
            return client
        except Exception:
            return None

    async def record_and_count(self, fingerprint: str, ticket_id: UUID, window_seconds: int) -> int:
        client = await self._client()
        now = time.time()
        key = f"corr:fp:{fingerprint}"
        if client:
            await client.zadd(key, {str(ticket_id): now})
            await client.zremrangebyscore(key, 0, now - window_seconds)
            await client.expire(key, window_seconds * 2)
            return int(await client.zcard(key))

        bucket = self._memory.setdefault(key, [])
        bucket.append((now, str(ticket_id)))
        self._memory[key] = [(ts, tid) for ts, tid in bucket if ts >= now - window_seconds]
        return len(self._memory[key])

    async def try_acquire_alert_lock(self, fingerprint: str, ttl_seconds: int) -> bool:
        client = await self._client()
        lock_key = f"corr:lock:{fingerprint}"
        now = time.time()
        if client:
            return bool(await client.set(lock_key, "1", nx=True, ex=ttl_seconds))
        expires = self._locks.get(lock_key, 0)
        if expires > now:
            return False
        self._locks[lock_key] = now + ttl_seconds
        return True
