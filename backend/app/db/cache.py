"""
Redis Cache Client
Async connection pool with helper methods
"""
import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


class CacheService:
    """High-level caching helpers."""

    def __init__(self, default_ttl: int = settings.CACHE_TTL_SECONDS):
        self.default_ttl = default_ttl

    async def get(self, key: str) -> Optional[Any]:
        r = await get_redis()
        try:
            value = await r.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.warning(f"Cache GET error for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        r = await get_redis()
        try:
            await r.setex(key, ttl or self.default_ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.warning(f"Cache SET error for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        r = await get_redis()
        try:
            await r.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache DELETE error for {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        r = await get_redis()
        try:
            keys = await r.keys(pattern)
            if keys:
                return await r.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache pattern delete error: {e}")
            return 0

    async def incr(self, key: str, ttl: Optional[int] = None) -> int:
        r = await get_redis()
        pipe = r.pipeline()
        await pipe.incr(key)
        if ttl:
            await pipe.expire(key, ttl)
        results = await pipe.execute()
        return results[0]

    async def exists(self, key: str) -> bool:
        r = await get_redis()
        return bool(await r.exists(key))


# Singleton instance
cache = CacheService()
