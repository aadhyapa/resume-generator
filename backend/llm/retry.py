from __future__ import annotations

import logging
from typing import Callable, TypeVar

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
