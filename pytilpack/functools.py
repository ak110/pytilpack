"""Pythonのユーティリティ集。"""

import asyncio
import functools
import inspect
import logging
import random
import time
import typing
import warnings

import pytilpack.http


def retry[**P, R](
    max_retries: int = 3,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 30.0,
    max_jitter: float = 0.5,
    includes: typing.Iterable[type[Exception]] | None = None,
    excludes: typing.Iterable[type[Exception]] | None = None,
    loglevel: int = logging.INFO,
    retry_status_codes: typing.Iterable[int] | None = (408, 429, 500, 502, 503, 504),
) -> typing.Callable[[typing.Callable[P, R]], typing.Callable[P, R]]:
    """リトライを行うデコレーター。

    - max_retriesが1の場合、待ち時間は1秒程度で2回呼ばれる。
    - max_retriesが2の場合、待ち時間は3秒程度で3回呼ばれる。
    - max_retriesが3の場合、待ち時間は7秒程度で4回呼ばれる。
    - 計算方法: sum(min(1.0 * (2.0 ** i), 30.0) for i in range(max_retries)) + ランダムなジッター

    requests/httpxのHTTPError例外にRetry-Afterヘッダーが含まれている場合、
    そちらを優先して待機時間を決定する。

    Args:
        max_retries: 最大リトライ回数
        initial_delay: 初回リトライ時の待機時間
        exponential_base: 待機時間の増加率
        max_delay: 最大待機時間
        max_jitter: 待機時間のランダムな増加率
        includes: リトライする例外のリスト
        excludes: リトライしない例外のリスト
        loglevel: ログレベル
        retry_status_codes: 発生した例外がHTTPエラーの場合にリトライするHTTPステータスコードのリスト。
            これにないエラーならリトライしない。
            Noneの場合、HTTPエラーでもステータスコードを判定しない。

    Returns:
        リトライを行うデコレーター

    """
    if includes is None:
        includes = (Exception,)
    if excludes is None:
        excludes = ()
    # 最大待機時間の目安
    total_delay = sum(min(initial_delay * (exponential_base**i), max_delay) for i in range(max_retries))
    total_delay = max(total_delay, 0.001)  # 念のため0秒は避ける

    def decorator(func: typing.Callable[P, R]) -> typing.Callable[P, R]:
        logger = logging.getLogger(func.__module__)

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs):
                # pylint: disable=catching-non-exception,raising-non-exception
                attempt = 0
                delay = initial_delay
                retry_after_total = 0.0
                while True:
                    try:
                        return await func(*args, **kwargs)
                    except tuple(excludes) as e:
                        raise e
                    except tuple(includes) as e:
                        attempt += 1
                        if attempt > max_retries:
                            raise e
                        # HTTPエラーの場合、ステータスコードを確認してリトライするか判定
                        if retry_status_codes is not None:
                            status_code = pytilpack.http.get_status_code_from_exception(e)
                            if status_code is not None and status_code not in retry_status_codes:
                                raise e
                        # Retry-Afterヘッダーがある場合、累積待機時間が本来の設定を超えるならエラーにする
                        if retry_after_total >= total_delay:
                            raise e
                        logger.log(
                            loglevel,
                            "%s: %s (retry %d/%d)",
                            func.__name__,
                            e,
                            attempt,
                            max_retries,
                        )
                        retry_after = pytilpack.http.get_retry_after_from_exception(e)
                        if retry_after is None:
                            # Exponential backoff with jitter
                            await asyncio.sleep(delay * random.uniform(1.0, 1.0 + max_jitter))
                            delay = min(delay * exponential_base, max_delay)
                        else:
                            # Retry-Afterヘッダーに従い待機
                            logger.log(loglevel, "Retry-After: %.1f", retry_after)
                            await asyncio.sleep(retry_after)
                            retry_after_total += retry_after

            return async_wrapper  # type: ignore[return-value]

        else:

            @functools.wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                # pylint: disable=catching-non-exception,raising-non-exception
                attempt = 0
                delay = initial_delay
                retry_after_total = 0.0
                while True:
                    try:
                        return func(*args, **kwargs)
                    except tuple(excludes) as e:
                        raise e
                    except tuple(includes) as e:
                        attempt += 1
                        if attempt > max_retries:
                            raise e
                        # HTTPエラーの場合、ステータスコードを確認してリトライするか判定
                        if retry_status_codes is not None:
                            status_code = pytilpack.http.get_status_code_from_exception(e)
                            if status_code is not None and status_code not in retry_status_codes:
                                raise e
                        # Retry-Afterヘッダーがある場合、累積待機時間が本来の設定を超えるならエラーにする
                        if retry_after_total >= total_delay:
                            raise e
                        logger.log(
                            loglevel,
                            "%s: %s (retry %d/%d)",
                            func.__name__,
                            e,
                            attempt,
                            max_retries,
                        )
                        retry_after = pytilpack.http.get_retry_after_from_exception(e)
                        if retry_after is None:
                            # Exponential backoff with jitter
                            time.sleep(delay * random.uniform(1.0, 1.0 + max_jitter))
                            delay = min(delay * exponential_base, max_delay)
                        else:
                            # Retry-Afterヘッダーに従い待機
                            logger.log(loglevel, "Retry-After: %.1f", retry_after)
                            time.sleep(retry_after)
                            retry_after_total += retry_after

            return sync_wrapper

    return decorator


def aretry[**P, R](
    max_retries: int = 3,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 30.0,
    max_jitter: float = 0.5,
    includes: typing.Iterable[type[Exception]] | None = None,
    excludes: typing.Iterable[type[Exception]] | None = None,
    loglevel: int = logging.INFO,
) -> typing.Callable[[typing.Callable[P, typing.Awaitable[R]]], typing.Callable[P, typing.Awaitable[R]]]:
    """非同期処理でリトライを行うデコレーター。"""
    if includes is None:
        includes = (Exception,)
    if excludes is None:
        excludes = ()

    warnings.warn("aretry is deprecated. Use retry instead.", DeprecationWarning, stacklevel=2)
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


def warn_if_slow[**P, R](
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

        else:

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
