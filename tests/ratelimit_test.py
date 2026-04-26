"""テストコード。"""

import time

import pytest

import pytilpack.ratelimit


@pytest.mark.asyncio
async def test_ratelimit_basic() -> None:
    """バースト内の取得が即座に完了することを確認。"""
    limiter = pytilpack.ratelimit.RateLimiter(rate=100, per=1.0)
    start = time.monotonic()
    for _ in range(10):
        await limiter.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.1  # ほぼ即座に完了するはず


@pytest.mark.asyncio
async def test_ratelimit_throttle() -> None:
    """レート制限により待機が発生することを確認。"""
    rate = 5
    per = 0.1  # refill_rate = 50 tok/sec
    limiter = pytilpack.ratelimit.RateLimiter(rate=rate, per=per)
    # バーストの2倍を要求することで、後半は必ず待機が発生する
    start = time.monotonic()
    for _ in range(rate * 2):
        await limiter.acquire()
    elapsed = time.monotonic() - start
    # 後半 rate 個のリクエストが各 per/rate 秒待機するため合計 per 秒以上かかる
    assert elapsed >= per * 0.5


@pytest.mark.asyncio
async def test_ratelimit_context_manager() -> None:
    """async withでの使用を確認。"""
    limiter = pytilpack.ratelimit.RateLimiter(rate=10, per=1.0)
    async with limiter:
        pass  # 正常に取得できることを確認
