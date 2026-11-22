__lazy_modules__ = ["asyncio", "multiprocessing", "threading", "typing"]

import asyncio
import multiprocessing
import threading
import typing


async def parallel[T](
    funcs: list[typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]]],
    max_workers: int | None = None,
    timeout: float | None = None,
) -> list[T]:
    semaphore = threading.Semaphore(max_workers if max_workers is not None else multiprocessing.cpu_count())

    def _thread(
        func: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]],
    ) -> T:
        with semaphore:
            return asyncio.run(func())

    tasks = [asyncio.to_thread(_thread, func) for func in funcs]
    if timeout is None:
        results = await asyncio.gather(*tasks)
    else:
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=timeout)
    return list(results)


async def parallel_for[T](func: typing.Callable[[int], typing.Awaitable[T]], n: int) -> list[T]:
    return await parallel([lambda i=i: func(i) for i in range(n)])  # type: ignore[misc]


async def parallel_foreach[T, U](func: typing.Callable[[U], typing.Awaitable[T]], items: typing.Iterable[U]) -> list[T]:
    return await parallel([lambda item=item: func(item) for item in items])  # type: ignore[misc]
