import os
import json
import logging
import redis.asyncio as redis
from typing import Optional, Any

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None

async def init_redis(url: str):
    global _redis_client
    if url:
        try:
            _redis_client = redis.from_url(url, decode_responses=True)
            await _redis_client.ping()
            logger.info("Redis connected successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            _redis_client = None

def get_redis():
    return _redis_client

async def cache_get(key: str) -> Optional[Any]:
    if not _redis_client:
        return None
    try:
        data = await _redis_client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.error(f"Redis get error for {key}: {e}")
        return None

async def cache_set(key: str, value: Any, ttl_seconds: int = 3600):
    if not _redis_client:
        return
    try:
        await _redis_client.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception as e:
        logger.error(f"Redis set error for {key}: {e}")

async def cache_delete(key: str):
    if not _redis_client:
        return
    try:
        await _redis_client.delete(key)
    except Exception as e:
        logger.error(f"Redis delete error for {key}: {e}")
