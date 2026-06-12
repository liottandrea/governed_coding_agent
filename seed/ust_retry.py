"""UST utility: retry decorator with exponential back-off.

Standard pattern used in UST integration code to wrap flaky external
calls (APIs, DB writes) with configurable retry logic.
"""
from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Callable, Iterable, TypeVar

F = TypeVar("F", bound=Callable)
logger = logging.getLogger(__name__)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Iterable[type[Exception]] = (Exception,),
) -> Callable[[F], F]:
    """Decorator: retry the wrapped function on specified exceptions.

    Args:
        max_attempts: Maximum number of total attempts (including the first).
        delay: Initial delay in seconds between attempts.
        backoff: Multiplier applied to delay after each failure.
        exceptions: Exception types that trigger a retry.

    Example:
        @retry(max_attempts=4, delay=0.5, exceptions=(TimeoutError, IOError))
        def fetch_data(url: str) -> bytes:
            ...
    """
    exc_tuple = tuple(exceptions)

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exc_tuple as exc:
                    if attempt == max_attempts:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__, max_attempts, exc,
                        )
                        raise
                    logger.warning(
                        "%s attempt %d/%d failed: %s — retrying in %.1fs",
                        func.__name__, attempt, max_attempts, exc, current_delay,
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

        return wrapper  # type: ignore[return-value]

    return decorator


class RetryableError(Exception):
    """Base class for errors that should be retried by the retry decorator."""
