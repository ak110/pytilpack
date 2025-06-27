"""テストコード。"""

import time

import pytest

import pytilpack.threadinga


@pytest.mark.asyncio
async def test_parallel():
    """parallelのテスト。"""

    async def func(x: int) -> int:
        return x + 1

    start = time.time()
    assert await pytilpack.threadinga.parallel(
        [lambda x=x: func(x) for x in range(3)]  # type: ignore[misc]
    ) == [1, 2, 3]
    duration = time.time() - start
    assert duration < 2  # 3つの処理が並列実行されるので2秒未満で完了するはず


@pytest.mark.asyncio
async def test_parallel_for():
    """parallel_forのテスト。"""

    async def func(x: int) -> int:
        return x + 1

    start = time.time()
    assert await pytilpack.threadinga.parallel_for(func, 3) == [1, 2, 3]
    duration = time.time() - start
    assert duration < 2  # 3つの処理が並列実行されるので2秒未満で完了するはず


@pytest.mark.asyncio
async def test_parallel_foreach():
    """parallel_foreachのテスト。"""

    async def func(x: int) -> int:
        return x + 1

    start = time.time()
    assert await pytilpack.threadinga.parallel_foreach(func, range(3)) == [1, 2, 3]
    duration = time.time() - start
    assert duration < 2  # 3つの処理が並列実行されるので2秒未満で完了するはず
