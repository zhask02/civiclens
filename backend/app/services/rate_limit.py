"""Redis-backed request limits for public reports and operator operations."""

import ipaddress
import logging
import os
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status

from app.auth import Principal, require_operator
from app.clients.redis import redis_client


logger = logging.getLogger(__name__)

# The script makes incrementing and assigning the first window's TTL one Redis
# operation.  A Python GET/INCR/EXPIRE sequence could race between API workers.
_FIXED_WINDOW_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return {count, redis.call('TTL', KEYS[1])}
"""


@dataclass(frozen=True)
class RateLimit:
    """An endpoint policy kept configurable without endpoint magic numbers."""

    limit: int
    window_seconds: int


def _positive_int(name: str, default: int) -> int:
    """Read a valid positive setting while retaining a safe v1 default."""
    value = os.getenv(name, str(default))
    try:
        parsed = int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a positive integer") from exc
    if parsed < 1:
        raise RuntimeError(f"{name} must be a positive integer")
    return parsed


def report_rate_limit() -> RateLimit:
    return RateLimit(
        limit=_positive_int("CIVICLENS_REPORT_RATE_LIMIT", 20),
        window_seconds=_positive_int("CIVICLENS_REPORT_RATE_WINDOW_SECONDS", 60),
    )


def operator_rate_limit() -> RateLimit:
    return RateLimit(
        limit=_positive_int("CIVICLENS_OPERATOR_RATE_LIMIT", 60),
        window_seconds=_positive_int("CIVICLENS_OPERATOR_RATE_WINDOW_SECONDS", 60),
    )


def normalized_client_ip(request: Request) -> str:
    """Return the socket peer IP; forwarded headers need trusted-proxy setup."""
    host = request.client.host if request.client else "unknown"
    try:
        return ipaddress.ip_address(host).compressed
    except ValueError:
        # Test transports or unusual server adapters may lack a parseable peer.
        # Keeping this one bounded fallback avoids trusting user-controlled headers.
        return "unknown"


def _enforce(key: str, policy: RateLimit) -> None:
    """Increment one Redis fixed-window counter or return a safe HTTP response."""
    try:
        count, ttl = redis_client.eval(
            _FIXED_WINDOW_SCRIPT,
            1,
            key,
            policy.window_seconds,
        )
    except Exception:
        # Availability wins in v1: Redis also backs non-critical caching, so a
        # Redis outage must not stop citizens reporting hazards or operators
        # managing the queue. Do log the condition without request credentials.
        logger.warning("Rate limiting unavailable; allowing request", exc_info=True)
        return

    if int(count) > policy.limit:
        retry_after = max(1, int(ttl))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


def limit_report_submission(request: Request) -> None:
    """Protect the public, expensive report pipeline before it is constructed."""
    _enforce(f"rate:reports:ip:{normalized_client_ip(request)}", report_rate_limit())


def limit_operator_request(
    principal: Principal = Depends(require_operator),
) -> None:
    """Isolate operator quotas by validated principal, never bearer token."""
    _enforce(f"rate:operator:{principal.name}", operator_rate_limit())
