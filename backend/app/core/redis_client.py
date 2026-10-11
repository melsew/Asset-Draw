from functools import lru_cache

import redis

from app.core.config import get_settings


@lru_cache
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, socket_connect_timeout=2)


def check_redis() -> None:
    """Raise if Redis is unreachable."""
    if not get_redis().ping():
        raise ConnectionError("redis ping failed")
