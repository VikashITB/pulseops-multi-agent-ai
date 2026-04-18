from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

RETRYABLE_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    OSError,
)


def async_retry(
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float = 30,
    retryable_exceptions: tuple[type[Exception], ...] = RETRYABLE_EXCEPTIONS,
):
    attempts = max_attempts or settings.agent_max_retries
    delay = base_delay or settings.agent_retry_base_delay

    def decorator(func: F):
        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(
                multiplier=delay,
                min=delay,
                max=max_delay,
            ),
            retry=retry_if_exception_type(retryable_exceptions),
            reraise=True,
        )
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def sync_retry(
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float = 30,
    retryable_exceptions: tuple[type[Exception], ...] = RETRYABLE_EXCEPTIONS,
):
    attempts = max_attempts or settings.agent_max_retries
    delay = base_delay or settings.agent_retry_base_delay

    def decorator(func: F):
        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(
                multiplier=delay,
                min=delay,
                max=max_delay,
            ),
            retry=retry_if_exception_type(retryable_exceptions),
            reraise=True,
        )
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator