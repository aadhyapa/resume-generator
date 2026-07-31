import hashlib
import hmac
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque

from fastapi import Header, HTTPException, Request, status


@dataclass(frozen=True)
class GenerateResumeSecuritySettings:
    """Runtime-configurable guardrails for expensive resume generation calls."""

    api_keys: tuple[str, ...]
    max_job_description_chars: int
    rate_limit_requests: int
    rate_limit_window_seconds: int

    @classmethod
    def from_env(cls) -> "GenerateResumeSecuritySettings":
        api_keys = tuple(
            key.strip()
            for key in os.getenv("GENERATE_RESUME_API_KEYS", "").split(",")
            if key.strip()
        )
        return cls(
            api_keys=api_keys,
            max_job_description_chars=_positive_int_from_env(
                "GENERATE_RESUME_MAX_JOB_DESCRIPTION_CHARS",
                12_000,
            ),
            rate_limit_requests=_positive_int_from_env(
                "GENERATE_RESUME_RATE_LIMIT_REQUESTS",
                10,
            ),
            rate_limit_window_seconds=_positive_int_from_env(
                "GENERATE_RESUME_RATE_LIMIT_WINDOW_SECONDS",
                60 * 60,
            ),
        )


def _positive_int_from_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    return value if value > 0 else default


class InMemoryRateLimiter:
    """
    Simple sliding-window limiter.

    This works for a single-process deployment. The class boundary keeps the app
    easy to migrate to Redis or another shared backend when the service scales to
    multiple workers or instances.
    """

    def __init__(self) -> None:
        self._requests_by_identity: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, identity: str, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        window_start = now - window_seconds

        with self._lock:
            requests = self._requests_by_identity[identity]
            while requests and requests[0] <= window_start:
                requests.popleft()

            if len(requests) >= limit:
                retry_after = max(1, int(requests[0] + window_seconds - now))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded for resume generation.",
                    headers={"Retry-After": str(retry_after)},
                )

            requests.append(now)


rate_limiter = InMemoryRateLimiter()


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None

    return token.strip()


async def require_generate_resume_access(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> str:
    """
    Authenticate and rate-limit calls that can spend external AI API credits.

    Clients may send either `X-API-Key: <key>` or
    `Authorization: Bearer <key>`. The function returns a stable caller identity
    that downstream code can use for logging or future per-user quota storage.
    """

    settings = GenerateResumeSecuritySettings.from_env()
    if not settings.api_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Resume generation is not configured for authenticated access.",
        )

    x_api_key = x_api_key if isinstance(x_api_key, str) else None
    authorization = authorization if isinstance(authorization, str) else None
    provided_key = x_api_key or _extract_bearer_token(authorization)
    if not provided_key or not any(
        hmac.compare_digest(provided_key, allowed_key)
        for allowed_key in settings.api_keys
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    client_host = request.client.host if request.client else "unknown"
    key_fingerprint = hashlib.sha256(provided_key.encode("utf-8")).hexdigest()[:12]
    identity = f"api-key:{key_fingerprint}:ip:{client_host}"
    rate_limiter.check(
        identity=identity,
        limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
    return identity


def validate_job_description_size(job_description: str) -> None:
    settings = GenerateResumeSecuritySettings.from_env()
    if len(job_description) > settings.max_job_description_chars:
        raise HTTPException(
            status_code=413,
            detail=(
                "Job description is too long. "
                f"Maximum length is {settings.max_job_description_chars} characters."
            ),
        )
