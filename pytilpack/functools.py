"""デコレーターとリトライのユーティリティ集。"""

import asyncio
import dataclasses
import functools
import inspect
import logging
import time
import typing

import pytilpack.http
import pytilpack.python
from pytilpack import _retry


class _Unset:
    """未指定を表すクラス。"""

    def __repr__(self) -> str:
        return "UNSET"


UNSET = _Unset()
"""未指定を表す値。"""


@dataclasses.dataclass
class Retry:
    """retry デコレーターの設定をオーバーライドするためのデータクラス。

    pytilpack.functools.retry デコレーターが適用された関数に対して、
    キーワード引数 `retry` にこのクラスのインスタンスを渡すことで、
    デコレーターの設定を関数呼び出し時にオーバーライドできる。
    """

    max_retries: int | _Unset = UNSET
    initial_delay: float | _Unset = UNSET
    exponential_base: float | _Unset = UNSET
    max_delay: float | _Unset = UNSET
    max_jitter: float | _Unset = UNSET
    includes: typing.Iterable[type[Exception]] | None | _Unset = UNSET
    excludes: typing.Iterable[type[Exception]] | None | _Unset = UNSET
    loglevel: int | _Unset = UNSET
    retry_status_codes: typing.Iterable[int] | None | _Unset = UNSET
    should_retry: typing.Callable[[Exception], bool] | None | _Unset = UNSET


@dataclasses.dataclass
class _RetryConfig:
    """retryデコレーター内部で使う実効設定。"""

    max_retries: int
    initial_delay: float
    exponential_base: float
    max_delay: float
    max_jitter: float
    includes: typing.Iterable[type[Exception]]
    excludes: typing.Iterable[type[Exception]]
    loglevel: int
    retry_status_codes: typing.Iterable[int] | None
    should_retry: typing.Callable[[Exception], bool] | None
    total_delay: float


@dataclasses.dataclass
class _RetryState:
    """同期・非同期リトライの判定と待機状態。"""

    cfg: _RetryConfig
    backoff: _retry.Backoff
    attempt: int = 0
    retry_after_total: float = 0.0
    retry_after: float | None = None

    def next_wait(self, exc: Exception, logger: logging.Logger, name: str) -> float:
        """元の判定順で次の待機時間を返し、打切り時は元例外を送出する。"""
        cfg = self.cfg
        if isinstance(exc, tuple(cfg.excludes)):
            raise exc
        self.attempt += 1
        if self.attempt > cfg.max_retries:
            raise exc
        if cfg.should_retry is not None and not cfg.should_retry(exc):
            raise exc
        if cfg.retry_status_codes is not None:
            status = pytilpack.http.get_status_code_from_exception(exc)
            if status is not None and status not in cfg.retry_status_codes:
                raise exc
        if self.retry_after_total >= cfg.total_delay:
            raise exc
        logger.log(cfg.loglevel, "%s: %s (retry %d/%d)", name, exc, self.attempt, cfg.max_retries)
        self.retry_after = pytilpack.http.get_retry_after_from_exception(exc)
        if self.retry_after is not None:
            logger.log(cfg.loglevel, "Retry-After: %.1f", self.retry_after)
        return self.backoff.wait(self.retry_after)

    def slept(self) -> None:
        """待機完了後だけ累積時間か指数バックオフを進める。"""
        if self.retry_after is None:
            self.backoff.advance()
        else:
            self.retry_after_total += self.retry_after


def _apply_retry_override(
    retry_override: typing.Any,
    max_retries: int,
    initial_delay: float,
    exponential_base: float,
    max_delay: float,
    max_jitter: float,
    includes: typing.Iterable[type[Exception]] | None,
    excludes: typing.Iterable[type[Exception]] | None,
    loglevel: int,
    retry_status_codes: typing.Iterable[int] | None,
    should_retry: typing.Callable[[Exception], bool] | None,
) -> _RetryConfig:
    """retry_overrideを反映した実効設定を返す。sync/async両wrapperで共用する。"""
    if retry_override is not None and isinstance(retry_override, Retry):
        if not isinstance(retry_override.max_retries, _Unset):
            max_retries = retry_override.max_retries
        if not isinstance(retry_override.initial_delay, _Unset):
            initial_delay = retry_override.initial_delay
        if not isinstance(retry_override.exponential_base, _Unset):
            exponential_base = retry_override.exponential_base
        if not isinstance(retry_override.max_delay, _Unset):
            max_delay = retry_override.max_delay
        if not isinstance(retry_override.max_jitter, _Unset):
            max_jitter = retry_override.max_jitter
        if not isinstance(retry_override.includes, _Unset):
            includes = retry_override.includes
        if not isinstance(retry_override.excludes, _Unset):
            excludes = retry_override.excludes
        if not isinstance(retry_override.loglevel, _Unset):
            loglevel = retry_override.loglevel
        if not isinstance(retry_override.retry_status_codes, _Unset):
            retry_status_codes = retry_override.retry_status_codes
        if not isinstance(retry_override.should_retry, _Unset):
            should_retry = retry_override.should_retry
    if includes is None:
        includes = (Exception,)
    if excludes is None:
        excludes = ()
    # 最大待機時間の目安（オーバーライド適用後の設定で計算）
    total_delay = sum(min(initial_delay * (exponential_base**i), max_delay) for i in range(max_retries))
    total_delay = max(total_delay, 0.001)  # 念のため0秒は避ける
    return _RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        exponential_base=exponential_base,
        max_delay=max_delay,
        max_jitter=max_jitter,
        includes=includes,
        excludes=excludes,
        loglevel=loglevel,
        retry_status_codes=retry_status_codes,
        should_retry=should_retry,
        total_delay=total_delay,
    )


def retry[**P, R](
    max_retries: int = 3,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 30.0,
    max_jitter: float = 0.5,
    includes: typing.Iterable[type[Exception]] | None = None,
    excludes: typing.Iterable[type[Exception]] | None = None,
    loglevel: int = logging.INFO,
    retry_status_codes: typing.Iterable[int] | None = (408, 429, 500, 502, 503, 504, 529),
    should_retry: typing.Callable[[Exception], bool] | None = None,
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
        should_retry: リトライするか否かを判定するcallable。
            引数に例外を受け取り、リトライする場合はTrue、しない場合はFalseを返す。
            Noneの場合、includes/excludesによる判定が使用される。
            includesやexcludesより細かい制御をしたいとき用。

    Returns:
        リトライを行うデコレーター

    Examples:
        非同期関数でのリトライ::

            @pytilpack.functools.retry(max_retries=3, initial_delay=1.0)
            async def call_external_api():
                ...

    """

    def decorator(func: typing.Callable[P, R]) -> typing.Callable[P, R]:
        logger = logging.getLogger(func.__module__)

        def state_for(kwargs: typing.Any) -> _RetryState:
            cfg = _apply_retry_override(
                kwargs.pop("retry", None),
                max_retries,
                initial_delay,
                exponential_base,
                max_delay,
                max_jitter,
                includes,
                excludes,
                loglevel,
                retry_status_codes,
                should_retry,
            )
            return _RetryState(cfg, _retry.Backoff(cfg.initial_delay, cfg.exponential_base, cfg.max_delay, cfg.max_jitter))

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs):
                state = state_for(kwargs)
                while True:
                    try:
                        return await func(*args, **kwargs)
                    except tuple(state.cfg.includes) as exc:  # pylint: disable=catching-non-exception
                        await asyncio.sleep(state.next_wait(exc, logger, func.__name__))
                        state.slept()

            return typing.cast(typing.Callable[P, R], async_wrapper)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            state = state_for(kwargs)
            while True:
                try:
                    return func(*args, **kwargs)
                except tuple(state.cfg.includes) as exc:  # pylint: disable=catching-non-exception
                    time.sleep(state.next_wait(exc, logger, func.__name__))
                    state.slept()

        return sync_wrapper

    return decorator


@pytilpack.python.deprecated("Use pytilpack.functools.retry instead.")
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

            return typing.cast(typing.Callable[P, R], async_wrapper)

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
