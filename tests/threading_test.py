import threading

import pytilpack.threading


def test_acquire_with_timeout():
    lock = threading.Lock()
    with pytilpack.threading.acquire_with_timeout(lock, 0.001) as acquired:
        assert acquired

    assert not lock.locked()
    with lock:
        with pytilpack.threading.acquire_with_timeout(lock, 0.001) as acquired:
            assert not acquired
        assert lock.locked()


def test_parallel():
    assert pytilpack.threading.parallel(
        [lambda x=x: x + 1 for x in range(3)]  # type: ignore[misc]
    ) == [1, 2, 3]


def test_parallel_for():
    assert pytilpack.threading.parallel_for(lambda x: x + 1, 3) == [1, 2, 3]


def test_parallel_foreach():
    assert pytilpack.threading.parallel_foreach(lambda x: x + 1, range(3)) == [1, 2, 3]
