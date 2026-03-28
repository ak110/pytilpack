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
    limiter = pytilpack.ratelimit.RateLimiter(rate=20, per=0.1)
    # 20トークンをすべて消費
    for _ in range(20):
        await limiter.acquire()
    # 次のacquireは待機が発生するはず (200トークン/秒なので約0.005秒)
    start = time.monotonic()
    await limiter.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.003  # 非ゼロの待機時間


@pytest.mark.asyncio
async def test_ratelimit_context_manager() -> None:
    """async withでの使用を確認。"""
    limiter = pytilpack.ratelimit.RateLimiter(rate=10, per=1.0)
    async with limiter:
        pass  # 正常に取得できることを確認
