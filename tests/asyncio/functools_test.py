"""テストコード。"""

import asyncio
import time

import pytest

import pytilpack.asyncio


@pytest.mark.asyncio
async def test_run_sync():
    """pytilpack.asyncio.run_syncのテスト。"""

    @pytilpack.asyncio.run_sync
    def sync_func(a: int, k: int) -> str:
        return str(a + k)

    assert await sync_func(1, k=2) == "3"


@pytest.mark.asyncio
async def test_acquire_with_timeout():
    lock = asyncio.Lock()
    async with pytilpack.asyncio.acquire_with_timeout(lock, 0.001) as acquired:
        assert acquired

    async with lock, pytilpack.asyncio.acquire_with_timeout(lock, 0.001) as acquired:
        assert not acquired


@pytest.mark.asyncio
async def async_func():
    await asyncio.sleep(0.0)
    return "Done"


@pytest.mark.asyncio(loop_scope="function")
async def test_run():
    await asyncio.to_thread(_sync_test_run)


def _sync_test_run():
    for _ in range(3):
        assert pytilpack.asyncio.run(async_func()) == "Done"


@pytest.mark.asyncio
async def test_run_async():
    for _ in range(3):
        assert pytilpack.asyncio.run(async_func()) == "Done"


@pytest.mark.asyncio
async def test_run_in_thread():
    """pytilpack.asyncio.run_in_threadのテスト。"""

    @pytilpack.asyncio.run_in_thread
    async def async_func_with_blocking(a: int, k: int) -> str:
        # 非同期処理
        await asyncio.sleep(0.01)
        # ブロッキング処理
        time.sleep(0.01)
        result = a + k
        return str(result)

    # 位置引数とキーワード引数のテスト
    assert await async_func_with_blocking(1, k=2) == "3"
    assert await async_func_with_blocking(10, k=20) == "30"
