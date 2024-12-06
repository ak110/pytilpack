"""Pythonのユーティリティ集。"""

import functools
import logging
import random
import time
import typing

T = typing.TypeVar("T")

logger = logging.getLogger(__name__)


def retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 30.0,
    max_jitter: float = 0.5,
    includes: typing.Iterable[type[Exception]] | None = None,
    excludes: typing.Iterable[type[Exception]] | None = None,
    loglevel: int = logging.INFO,
) -> typing.Callable:
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

    def decorator(func: typing.Callable) -> typing.Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
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
                        retry_count + 1,
                        max_retries,
                    )
                    time.sleep(delay * random.uniform(1.0, 1.0 + max_jitter))
                    delay = min(delay * exponential_base, max_delay)

        return wrapper

    return decorator
