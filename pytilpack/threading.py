__lazy_modules__ = ["concurrent.futures", "contextlib", "typing"]

import concurrent.futures
import contextlib
import typing

if typing.TYPE_CHECKING:
    import threading  # noqa: TID254  # 型チェック専用で実行時に読み込まれないため列挙しない


@contextlib.contextmanager
def acquire_with_timeout(
    lock: "threading.Lock | threading.RLock | threading.Semaphore | threading.BoundedSemaphore",
    timeout: float,
) -> typing.Generator[bool, None, None]:
    acquired = lock.acquire(timeout=timeout)
    try:
        yield acquired
    finally:
        if acquired:
            lock.release()


def parallel[T](
    funcs: typing.Iterable[typing.Callable[[], T]],
    max_workers: int | None = None,
    thread_name_prefix: str = "",
    timeout: float | None = None,
    chunksize: int = 1,
) -> list[T]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=thread_name_prefix) as executor:
        return list(executor.map(lambda f: f(), funcs, timeout=timeout, chunksize=chunksize))


def parallel_for[T](func: typing.Callable[[int], T], n: int) -> list[T]:
    return parallel([lambda i=i: func(i) for i in range(n)])  # type: ignore[misc]


def parallel_foreach[T, U](func: typing.Callable[[U], T], items: typing.Iterable[U]) -> list[T]:
    return parallel([lambda item=item: func(item) for item in items])  # type: ignore[misc]
