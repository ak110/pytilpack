"""テストコード。"""

import asyncio

import pytest

import pytilpack.asyncio.threadpool


async def _async_add(a: int, b: int) -> int:
    """非同期加算。"""
    await asyncio.sleep(0.001)
    return a + b


async def _async_mul(a: int, b: int) -> int:
    """非同期乗算。"""
    await asyncio.sleep(0.001)
    return a * b


def test_thread_pool_submit() -> None:
    """ThreadPool.submitのテスト。"""
    with pytilpack.asyncio.threadpool.ThreadPool(max_workers=2) as pool:
        future = pool.submit(_async_add(1, 2))
        assert future.result(timeout=1) == 3

        future = pool.submit(_async_mul(3, 4))
        assert future.result(timeout=1) == 12


def test_thread_pool_map() -> None:
    """ThreadPool.mapのテスト。"""
    with pytilpack.asyncio.threadpool.ThreadPool(max_workers=2) as pool:
        coros = [_async_add(i, i + 1) for i in range(5)]
        futures = pool.map(coros)
        assert len(futures) == 5
        results = [f.result(timeout=1) for f in futures]
        assert results == [1, 3, 5, 7, 9]


def test_thread_pool_shutdown() -> None:
    """ThreadPool.shutdownのテスト。"""
    pool = pytilpack.asyncio.threadpool.ThreadPool(max_workers=2)
    pool.submit(_async_add(1, 2))
    pool.shutdown()
    # shutdownで完全に停止していることを確認
    for worker in pool.workers:
        assert worker.thread is None


@pytest.mark.asyncio
async def test_thread_pool_ashutdown() -> None:
    """ThreadPool.ashutdownのテスト。"""
    pool = pytilpack.asyncio.threadpool.ThreadPool(max_workers=2)
    pool.submit(_async_add(1, 2))
    await pool.ashutdown()
    # ashutdownで完全に停止していることを確認
    for worker in pool.workers:
        assert worker.thread is None


@pytest.mark.asyncio
async def test_thread_pool_async_context_manager() -> None:
    """ThreadPoolの非同期コンテキストマネージャーのテスト。"""
    async with pytilpack.asyncio.threadpool.ThreadPool(max_workers=2) as pool:
        future = pool.submit(_async_add(5, 6))
        assert future.result(timeout=1) == 11
    # コンテキストを抜けたら停止していることを確認
    for worker in pool.workers:
        assert worker.thread is None


def test_worker_thread() -> None:
    """WorkerThreadのテスト。"""
    worker = pytilpack.asyncio.threadpool.WorkerThread(name="test-worker")
    worker.start()
    future = worker.submit(_async_add(10, 20))
    assert future.result(timeout=1) == 30
    worker.stop()
    assert worker.thread is None


def test_thread_pool_destructor(caplog: pytest.LogCaptureFixture) -> None:
    """ThreadPoolのデストラクタのテスト。"""
    with caplog.at_level("WARNING"):
        pool = pytilpack.asyncio.threadpool.ThreadPool(max_workers=2)
        pool.submit(_async_add(1, 2))
        # shutdownを呼ばずにdelすると警告が出る
        del pool
        assert "ThreadPool is being destroyed with" in caplog.text
