import asyncio
import types

import pytest

import pytilpack.ratelimit


@pytest.mark.asyncio
async def test_ratelimit_burst_and_refill(monkeypatch: pytest.MonkeyPatch) -> None:
    now = 0.0
    delays: list[float] = []

    async def advance(delay: float) -> None:
        nonlocal now
        assert len(delays) < 2
        delays.append(delay)
        now += delay

    monkeypatch.setattr(pytilpack.ratelimit, "time", types.SimpleNamespace(monotonic=lambda: now))
    monkeypatch.setattr(pytilpack.ratelimit, "asyncio", types.SimpleNamespace(Lock=asyncio.Lock, sleep=advance))
    limiter = pytilpack.ratelimit.RateLimiter(rate=2, per=1)
    async with limiter:
        await limiter.acquire()
        assert now == 0
    await limiter.acquire()
    assert delays == [0.5]

    now += 10
    await limiter.acquire()
    await limiter.acquire()
    assert delays == [0.5]
    await limiter.acquire()
    assert delays == [0.5, 0.5]
