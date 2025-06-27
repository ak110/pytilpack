"""Pythonのユーティリティ集。"""

import asyncio
import functools
import inspect
import logging
import random
import time
import typing
import warnings

T = typing.TypeVar("T")
P = typing.ParamSpec("P")
R = typing.TypeVar("R")


def retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 30.0,
    max_jitter: float = 0.5,
    includes: typing.Iterable[type[Exception]] | None = None,
    excludes: typing.Iterable[type[Exception]] | None = None,
    loglevel: int = logging.INFO,
) -> typing.Callable[[typing.Callable[P, R]], typing.Callable[P, R]]:
    """リトライを行うデコレーター。

    - max_retriesが1の場合、待ち時間は1秒程度で2回呼ばれる。
    - max_retriesが2の場合、待ち時間は3秒程度で3回呼ばれる。
    - max_retriesが3の場合、待ち時間は7秒程度で4回呼ばれる。

    Args:
        max_retries: 最大リトライ回数
        initial_delay: 初回リトライ時の待機時間
        exponential_base: 待機時間の増加率
        max_delay: 最大待機時間
        max_jitter: 待機時間のランダムな増加率
        includes: リトライする例外のリスト
        excludes: リトライしない例外のリスト

    Returns:
        リトライを行うデコレーター

    """
    if includes is None:
        includes = (Exception,)
    if excludes is None:
        excludes = ()

    def decorator(func: typing.Callable[P, R]) -> typing.Callable[P, R]:
        logger = logging.getLogger(func.__module__)

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs):
                # pylint: disable=catching-non-exception,raising-non-exception
                retry_count = 0
                delay = initial_delay
                while True:
                    try:
                        return await func(*args, **kwargs)
                    except tuple(excludes) as e:
                        raise e
                    except tuple(includes) as e:
                        retry_count += 1
                        if retry_count > max_retries:
                            raise e
                        logger.log(
                            loglevel,
                            "%s: %s (retry %d/%d)",
                            func.__name__,
                            e,
                            retry_count,
                            max_retries,
                        )
                        await asyncio.sleep(
                            delay * random.uniform(1.0, 1.0 + max_jitter)
                        )
                        delay = min(delay * exponential_base, max_delay)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # pylint: disable=catching-non-exception,raising-non-exception
            retry_count = 0
            delay = initial_delay
            while True:
                try:
                    return func(*args, **kwargs)
                except tuple(excludes) as e:
                    raise e
                except tuple(includes) as e:
                    retry_count += 1
                    if retry_count > max_retries:
                        raise e
                    logger.log(
                        loglevel,
                        "%s: %s (retry %d/%d)",
                        func.__name__,
                        e,
                        retry_count,
                        max_retries,
                    )
                    time.sleep(delay * random.uniform(1.0, 1.0 + max_jitter))
                    delay = min(delay * exponential_base, max_delay)

        return sync_wrapper

    return decorator


def aretry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 30.0,
    max_jitter: float = 0.5,
    includes: typing.Iterable[type[Exception]] | None = None,
    excludes: typing.Iterable[type[Exception]] | None = None,
    loglevel: int = logging.INFO,
) -> typing.Callable[
    [typing.Callable[P, typing.Awaitable[R]]], typing.Callable[P, typing.Awaitable[R]]
]:
    """非同期処理でリトライを行うデコレーター。"""
    if includes is None:
        includes = (Exception,)
    if excludes is None:
        excludes = ()

    warnings.warn(
        "aretry is deprecated. Use retry instead.", DeprecationWarning, stacklevel=2
    )
    return retry(
        max_retries=max_retries,
        initial_delay=initial_delay,
        exponential_base=exponential_base,
        max_delay=max_delay,
        max_jitter=max_jitter,
        includes=includes,
        excludes=excludes,
        loglevel=loglevel,
    )


def warn_if_slow(
    threshold_seconds: float = 0.001,
) -> typing.Callable[[typing.Callable[P, R]], typing.Callable[P, R]]:
    """処理に一定以上の時間がかかっていたら警告ログを出力するデコレーター。

    Args:
        threshold_seconds: 警告ログを記録するまでの秒数。既定値は1ミリ秒。
    """

    def decorator(func: typing.Callable[P, R]) -> typing.Callable[P, R]:
        logger = logging.getLogger(func.__module__)

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs):
                start = time.perf_counter()
                result = await func(*args, **kwargs)
                duration = time.perf_counter() - start
                if duration >= threshold_seconds:
                    logger.warning(
                        "Function %s took %.3f s (threshold %.3f s)",
                        func.__qualname__,
                        duration,
                        threshold_seconds,
                    )
                return result

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start
            if duration >= threshold_seconds:
                logger.warning(
                    "Function %s took %.3f s (threshold %.3f s)",
                    func.__qualname__,
                    duration,
                    threshold_seconds,
                )
            return result

        return sync_wrapper

    return decorator
