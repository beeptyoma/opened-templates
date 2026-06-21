import redis.asyncio as redis
from core.settings import settings

_client: redis.Redis | None = None

def init_redis() -> None:
    global _client
    _client = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None

def get_redis() -> redis.Redis:
    assert _client is not None, "redis client not initialized — call init_redis() on startup"
    return _client
