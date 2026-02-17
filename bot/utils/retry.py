"""Async retry with exponential backoff and jitter."""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Callable, Awaitable

import aiohttp

logger = logging.getLogger("whalegod.retry")


async def retry_async(
    coro_func: Callable[[], Awaitable[Any]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retry_on: tuple[type[Exception], ...] = (aiohttp.ClientError, asyncio.TimeoutError),
    retry_on_status: tuple[int, ...] = (429, 500, 502, 503, 504),
) -> Any | None:
    """Retry an async callable with exponential backoff + jitter.

    Returns the result on success or ``None`` after all retries are exhausted.
    On 429 responses the ``Retry-After`` header is respected when present.
    """
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 2):  # attempt 1 = first try
        try:
            result = await coro_func()

            # Handle aiohttp responses with retryable status codes
            if isinstance(result, aiohttp.ClientResponse):
                if result.status in retry_on_status:
                    delay = base_delay * (2 ** (attempt - 1))
                    if result.status == 429:
                        retry_after = result.headers.get("Retry-After")
                        if retry_after:
                            try:
                                delay = float(retry_after)
                            except ValueError:
                                pass
                    delay = min(delay, max_delay)
                    jitter = delay * random.uniform(0, 0.25)
                    delay += jitter
                    # Release the response before retrying to avoid resource leak
                    result.release()
                    if attempt <= max_retries:
                        logger.warning(
                            "Retry %d/%d — HTTP %d, waiting %.1fs",
                            attempt, max_retries, result.status, delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    logger.error(
                        "All %d retries exhausted — last HTTP %d",
                        max_retries, result.status,
                    )
                    return None
            return result

        except retry_on as exc:
            last_exc = exc
            if attempt > max_retries:
                break
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            jitter = delay * random.uniform(0, 0.25)
            delay += jitter
            logger.warning(
                "Retry %d/%d — %s: %s, waiting %.1fs",
                attempt, max_retries, type(exc).__name__, exc, delay,
            )
            await asyncio.sleep(delay)

    logger.error("All %d retries exhausted — last error: %s", max_retries, last_exc)
    return None
