"""非同期I/O関連。"""

import asyncio
import concurrent.futures
import contextlib
import contextvars
import functools
import inspect
import logging
import typing

logger = logging.getLogger(__name__)


def ensure_async[**P, R](
    func: typing.Callable[P, typing.Awaitable[R] | R],
) -> typing.Callable[P, typing.Awaitable[R]]:
    """関数が非同期関数でない場合、非同期関数に変換するデコレーター。"""
    if inspect.iscoroutinefunction(func):
        return typing.cast(typing.Callable[P, typing.Awaitable[R]], func)
    else:
        return run_sync(typing.cast(typing.Callable[P, R], func))


def run_sync[**P, R](
    func: typing.Callable[P, R],
) -> typing.Callable[P, typing.Awaitable[R]]:
    """同期関数を非同期に実行するデコレーター。

    quart.utils.run_syncのquart関係ない版。
    """

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return await asyncio.to_thread(func, *args, **kwargs)

    return wrapper


def run_in_thread[**P, R](
    func: typing.Callable[P, typing.Coroutine[typing.Any, typing.Any, R]],
) -> typing.Callable[P, typing.Awaitable[R]]:
    """非同期関数を非同期に実行するデコレーター。

    awaitも使うけどブロッキング処理も含まれるような関数を雑に何とかするためのもの。
    """

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        ctx = contextvars.copy_context()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(ctx.run, lambda: asyncio.run(func(*args, **kwargs)))
            return await asyncio.wrap_future(future)

    return wrapper


@contextlib.asynccontextmanager
async def acquire_with_timeout(lock: asyncio.Lock | asyncio.Semaphore, timeout: float) -> typing.AsyncGenerator[bool, None]:
    """ロックを取得し、タイムアウト時間内に取得できなかった場合はFalseを返す。

    Args:
        lock: 取得するロック。
        timeout: タイムアウト時間（秒）。

    Returns:
        ロックが取得できた場合はTrue、取得できなかった場合はFalse。

    """
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
    """非同期関数を実行する。"""
    # https://github.com/microsoftgraph/msgraph-sdk-python/issues/366#issuecomment-1830756182
    loop: asyncio.AbstractEventLoop | None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    # 非同期環境でない場合
    # (スタックトレースをシンプルにするためexceptの外で実行)
    if loop is None:
        return asyncio.run(coro)

    # 何らかの理由でイベントループは存在するが動いてない場合 (謎)
    if not loop.is_running():
        return loop.run_until_complete(coro)

    # 現在のスレッドでイベントループが実行されている場合
    # 別スレッド・別イベントループで実行する
    ctx = contextvars.copy_context()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(ctx.run, lambda: asyncio.run(coro))
        return future.result()
