"""テストコード。"""

import threading

import pytest

import pytilpack.threadinga


@pytest.fixture(autouse=True)
def _three_workers(monkeypatch: pytest.MonkeyPatch) -> None:
    """CPU数にかかわらず、同時実行を観測する処理数にワーカー数をそろえる。"""
    monkeypatch.setattr(pytilpack.threadinga.multiprocessing, "cpu_count", lambda: 3)


@pytest.mark.asyncio
async def test_parallel():
    """parallelが3つの処理を同時に実行する。"""
    barrier = threading.Barrier(3, timeout=5)

    async def func(x: int) -> int:
        barrier.wait()
        return x + 1

    assert await pytilpack.threadinga.parallel(
        [lambda x=x: func(x) for x in range(3)]  # type: ignore[misc]
    ) == [1, 2, 3]


@pytest.mark.asyncio
async def test_parallel_for():
    """parallel_forが3つの処理を同時に実行する。"""
    barrier = threading.Barrier(3, timeout=5)

    async def func(x: int) -> int:
        barrier.wait()
        return x + 1

    assert await pytilpack.threadinga.parallel_for(func, 3) == [1, 2, 3]


@pytest.mark.asyncio
async def test_parallel_foreach():
    """parallel_foreachが3つの処理を同時に実行する。"""
    barrier = threading.Barrier(3, timeout=5)

    async def func(x: int) -> int:
        barrier.wait()
        return x + 1

    assert await pytilpack.threadinga.parallel_foreach(func, range(3)) == [1, 2, 3]
