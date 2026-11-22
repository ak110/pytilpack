__lazy_modules__ = ["asyncio", "concurrent.futures", "contextlib", "contextvars", "functools", "inspect", "logging", "typing"]

import asyncio
import concurrent.futures
import contextlib
import contextvars
import functools
import inspect
import logging
import typing

logger = logging.getLogger(__name__)

__all__ = ["ensure_async", "run_sync", "run_in_thread", "acquire_with_timeout", "run"]


def ensure_async[**P, R](
    func: typing.Callable[P, typing.Awaitable[R] | R],
) -> typing.Callable[P, typing.Awaitable[R]]:
    if inspect.iscoroutinefunction(func):
        return typing.cast(typing.Callable[P, typing.Awaitable[R]], func)
    else:
        return run_sync(typing.cast(typing.Callable[P, R], func))


def run_sync[**P, R](
    func: typing.Callable[P, R],
) -> typing.Callable[P, typing.Awaitable[R]]:

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return await asyncio.to_thread(func, *args, **kwargs)

    return wrapper


def run_in_thread[**P, R](
    func: typing.Callable[P, typing.Coroutine[typing.Any, typing.Any, R]],
) -> typing.Callable[P, typing.Awaitable[R]]:

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        ctx = contextvars.copy_context()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(ctx.run, lambda: asyncio.run(func(*args, **kwargs)))
            return await asyncio.wrap_future(future)

    return wrapper


@contextlib.asynccontextmanager
async def acquire_with_timeout(lock: asyncio.Lock | asyncio.Semaphore, timeout: float) -> typing.AsyncGenerator[bool, None]:
    try:
        await asyncio.wait_for(lock.acquire(), timeout=timeout)
        acquired = True
    except TimeoutError:
        acquired = False

    try:
        yield acquired
    finally:
        if acquired:
            lock.release()


def run[T](coro: typing.Coroutine[typing.Any, typing.Any, T]) -> T:
    # https://github.com/microsoftgraph/msgraph-sdk-python/issues/366#issuecomment-1830756182
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None:
        return asyncio.run(coro)

    ctx = contextvars.copy_context()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(ctx.run, lambda: asyncio.run(coro))
        return future.result()
