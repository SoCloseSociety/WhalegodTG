"""Generic async token-bucket rate limiter for API calls."""

from __future__ import annotations

import asyncio
import logging
import time

logger = logging.getLogger("whalegod.rate_limiter")


class AsyncRateLimiter:
    """Token-bucket rate limiter that works as an async context manager.

    Usage::

        limiter = AsyncRateLimiter("helius", max_calls=10, period=1.0)
        async with limiter:
            resp = await session.get(url)
    """

    def __init__(self, name: str, max_calls: int, period: float) -> None:
        self.name = name
        self.max_calls = max_calls
        self.period = period
        self._tokens: float = float(max_calls)
        self._last_refill: float = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        """Add tokens based on elapsed time since last refill."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        new_tokens = elapsed * (self.max_calls / self.period)
        self._tokens = min(self.max_calls, self._tokens + new_tokens)
        self._last_refill = now

    async def acquire(self) -> None:
        """Wait until a token is available, then consume one."""
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait_time = (1.0 - self._tokens) * (self.period / self.max_calls)
            logger.debug("Rate limiter [%s] waiting %.2fs", self.name, wait_time)
            await asyncio.sleep(wait_time)

    async def __aenter__(self) -> AsyncRateLimiter:
        await self.acquire()
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


# ---------------------------------------------------------------------------
# Pre-configured limiters (importable from config or here)
# ---------------------------------------------------------------------------

RATE_LIMITERS: dict[str, AsyncRateLimiter] = {
    "helius":               AsyncRateLimiter("helius", max_calls=10, period=1.0),
    "etherscan":            AsyncRateLimiter("etherscan", max_calls=5, period=1.0),
    "alchemy":              AsyncRateLimiter("alchemy", max_calls=25, period=1.0),
    "dexscreener_pairs":    AsyncRateLimiter("dexscreener_pairs", max_calls=290, period=60.0),
    "dexscreener_profiles": AsyncRateLimiter("dexscreener_profiles", max_calls=55, period=60.0),
    "jupiter":              AsyncRateLimiter("jupiter", max_calls=5, period=1.0),
    "coingecko":            AsyncRateLimiter("coingecko", max_calls=25, period=60.0),
    "telegram":             AsyncRateLimiter("telegram", max_calls=25, period=1.0),
}
