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


async def _independent_coro() -> str:
    await asyncio.sleep(0)
    return "ok"


@pytest.mark.asyncio(loop_scope="function")
async def test_run_preserves_parent_loop_queue() -> None:
    """``run`` 呼び出しの前後で親ループの ``Queue`` を継続操作できることを確認する。

    ``coro`` は独立リソースのみを使い、親ループ起源リソースは ``run`` 呼び出し外で操作する。
    """
    queue: asyncio.Queue[str] = asyncio.Queue()
    await queue.put("before")

    assert pytilpack.asyncio.run(_independent_coro()) == "ok"

    assert await queue.get() == "before"
    await queue.put("after")
    assert await queue.get() == "after"


@pytest.mark.asyncio(loop_scope="function")
async def test_run_preserves_parent_loop_background_task() -> None:
    """``run`` 呼び出し完了後も親ループ上のバックグラウンドタスクが完了まで継続実行できることを確認する。"""
    progress: list[int] = []

    async def background() -> None:
        for i in range(3):
            progress.append(i)
            await asyncio.sleep(0)

    task = asyncio.create_task(background())
    await asyncio.sleep(0)

    assert pytilpack.asyncio.run(_independent_coro()) == "ok"

    await task
    assert progress == [0, 1, 2]


def test_run_from_non_async_context() -> None:
    """非async環境からの ``run`` 呼び出しが成功することを確認する。"""
    assert pytilpack.asyncio.run(_independent_coro()) == "ok"


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
