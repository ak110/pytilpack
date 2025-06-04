"""テストコード。"""

import threading

import pytilpack.threading_


async def test_acquire_with_timeout():
    lock = threading.Lock()
    with pytilpack.threading_.acquire_with_timeout(lock, 0.001) as acquired:
        assert acquired

    with lock:
        with pytilpack.threading_.acquire_with_timeout(lock, 0.001) as acquired:
            assert not acquired


def test_parallel():
    assert pytilpack.threading_.parallel(
        [lambda x=x: x + 1 for x in range(3)]  # type: ignore[misc]
    ) == [1, 2, 3]


def test_parallel_for():
    assert pytilpack.threading_.parallel_for(lambda x: x + 1, 3) == [1, 2, 3]


def test_parallel_foreach():
    assert pytilpack.threading_.parallel_foreach(lambda x: x + 1, range(3)) == [1, 2, 3]
