import time

import pytest

import pytilpack.ratelimit


@pytest.mark.asyncio
async def test_ratelimit_basic() -> None:
    limiter = pytilpack.ratelimit.RateLimiter(rate=100, per=1.0)
    start = time.monotonic()
    for _ in range(10):
        await limiter.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.1


@pytest.mark.asyncio
async def test_ratelimit_throttle() -> None:
    rate = 5
    per = 0.1
    limiter = pytilpack.ratelimit.RateLimiter(rate=rate, per=per)
    start = time.monotonic()
    for _ in range(rate * 2):
        await limiter.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= per * 0.5


@pytest.mark.asyncio
async def test_ratelimit_context_manager() -> None:
    limiter = pytilpack.ratelimit.RateLimiter(rate=10, per=1.0)
    async with limiter:
        pass
