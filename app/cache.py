import json

import redis

from app.config import settings

redis_client = redis.from_url(settings.redis_url, decode_responses=True)

# Applied to every cached value so a stale cache format from an older
# deploy doesn't get misread as valid data after a schema change.
CACHE_VERSION = "v1"

DASHBOARD_CACHE_TTL_SECONDS = 60


def dashboard_cache_key(user_id: int) -> str:
    return f"{CACHE_VERSION}:dashboard:user:{user_id}"


def get_cached_json(key: str):
    raw = redis_client.get(key)
    if raw is None:
        return None
    return json.loads(raw)


def set_cached_json(key: str, value, ttl_seconds: int) -> None:
    redis_client.set(key, json.dumps(value), ex=ttl_seconds)


def invalidate_dashboard_cache(user_id: int) -> None:
    """Called on any Application create/update/delete for this user."""
    redis_client.delete(dashboard_cache_key(user_id))
