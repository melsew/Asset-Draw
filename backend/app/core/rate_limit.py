"""Redis fixed-window rate limiting without storing raw phone numbers or IPs in keys."""
from __future__ import annotations

import hashlib

from redis import Redis


class RateLimitExceeded(Exception):
    """Raised when a caller exceeds a named rate limit."""


def enforce_rate_limit(
    client: Redis,
    *,
    scope: str,
    identity: str,
    limit: int,
    window_seconds: int,
) -> None:
    identity_hash = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    key = f"asset-draw:rate:{scope}:{identity_hash}"
    pipeline = client.pipeline(transaction=True)
    pipeline.incr(key)
    pipeline.expire(key, window_seconds, nx=True)
    count, _ = pipeline.execute()
    if int(count) > limit:
        raise RateLimitExceeded(scope)