from __future__ import annotations

import logging
from typing import Callable, TypeVar

import time
import anthropic
from google.genai import errors as genai_errors

T = TypeVar("T")

logger = logging.getLogger(__name__)


def call_with_validation_retry(attempt: Callable[[], T], *, attempts: int = 2, label: str = "LLM call") -> T:
    """Run `attempt()` and retry on ValueError (a failed post-hoc validation, e.g.
    a hallucinated ID or an altered fact), not on every exception - a malformed
    request or an auth error will fail identically on retry, so only a validation
    failure (which reflects one bad generation, not a bad request) is worth
    re-rolling for.

    Schema-level guards (enum-constrained IDs, strict tool schemas) should make
    the failures this catches rare. This exists for the residual case - the
    model satisfies the schema but still fails a semantic check the schema can't
    express (e.g. bullet order, unchanged numeric facts) - so one bad generation
    doesn't surface as a 500 to the end user.
    """
    last_error: ValueError | None = None
    for attempt_number in range(1, attempts + 1):
        try:
            return attempt()
        except ValueError as e:
            last_error = e
            logger.warning("%s failed validation on attempt %d/%d: %s", label, attempt_number, attempts, e)
    assert last_error is not None
    raise last_error


def call_with_transient_retry(
    attempt: Callable[[], T],
    *,
    attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    label: str = "LLM call",
) -> T:
    """Run `attempt()` and retry on transient errors (timeouts, rate limits, 5xx)."""
    delay = initial_delay
    for attempt_number in range(1, attempts + 1):
        try:
            return attempt()
        except (
            anthropic.InternalServerError,
            anthropic.APITimeoutError,
            anthropic.APIConnectionError,
            anthropic.RateLimitError,
        ) as e:
            if attempt_number == attempts:
                logger.error("%s failed with transient Anthropic error on final attempt %d/%d: %s", label, attempt_number, attempts, e)
                raise
            logger.warning(
                "%s failed with transient Anthropic error on attempt %d/%d. Retrying in %.2fs. Error: %s",
                label,
                attempt_number,
                attempts,
                delay,
                e,
            )
        except genai_errors.APIError as e:
            # Retry on 429 (Rate Limit) or 5xx (Server Error)
            is_transient = e.code == 429 or (e.code is not None and 500 <= e.code < 600)
            if not is_transient:
                raise
            if attempt_number == attempts:
                logger.error("%s failed with transient Gemini error on final attempt %d/%d: %s", label, attempt_number, attempts, e)
                raise
            logger.warning(
                "%s failed with transient Gemini error on attempt %d/%d. Retrying in %.2fs. Error: %s",
                label,
                attempt_number,
                attempts,
                delay,
                e,
            )
        time.sleep(delay)
        delay *= backoff_factor
    # Fallback to satisfy typing, though code should return or raise above
    raise RuntimeError("Unexpected end of retry loop")
