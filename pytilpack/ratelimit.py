__lazy_modules__ = ["asyncio", "time", "typing"]

import asyncio
import time
import typing


class RateLimiter:
    def __init__(self, rate: float, per: float = 1.0) -> None:
        self._max_tokens = rate
        self._tokens = rate
        self._refill_rate = rate / per
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait_time = (1.0 - self._tokens) / self._refill_rate
            await asyncio.sleep(wait_time)

    async def __aenter__(self) -> "RateLimiter":  # noqa: D105
        await self.acquire()
        return self

    async def __aexit__(self, *args: typing.Any) -> None:  # noqa: D105
        del args  # noqa

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._max_tokens, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now
