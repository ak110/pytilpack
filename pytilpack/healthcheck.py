"""ヘルスチェック機能の実装用ヘルパー。"""

import asyncio
import datetime
import functools
import logging
import time
import typing

import pytilpack.logging

P = typing.ParamSpec("P")
R = typing.TypeVar("R")

CheckerType = typing.Callable[[], typing.Awaitable[None]]
"""ヘルスチェック関数の型。"""

CheckerEntry = tuple[str, CheckerType]
"""ヘルスチェックの名前と関数を持つタプル。"""

CheckerEntries = list[CheckerEntry]
"""ヘルスチェックの名前と関数のリスト。"""

startup_time = datetime.datetime.now()
"""アプリケーションの起動時間を記録する変数。ヘルスチェックの uptime に使用される。"""

logger = logging.getLogger(__name__)


class HealthCheckDetail(typing.TypedDict):
    """ヘルスチェックの詳細を表す型。"""

    status: typing.Literal["ok", "fail"]
    response_time_ms: float
    error: typing.NotRequired[str]


class HealthCheckResult(typing.TypedDict):
    """ヘルスチェックの結果を表す型。"""

    status: typing.Literal["ok", "fail"]
    checked: str
    uptime: str
    details: typing.NotRequired[dict[str, HealthCheckDetail]]


def make_entry(
    name: str,
    func: (
        typing.Callable[P, None]
        | typing.Callable[P, R]
        | typing.Callable[P, typing.Awaitable[None]]
        | typing.Callable[P, typing.Awaitable[R]]
    ),
    /,
    *args: P.args,
    **kwargs: P.kwargs,
) -> CheckerEntry:
    """CheckerEntryを作成する。

    Args:
        name: ヘルスチェックの名前。
        func: ヘルスチェック関数。
        *args: ヘルスチェック関数に渡す引数。
        **kwargs: ヘルスチェック関数に渡すキーワード引数。

    Returns:
        ヘルスチェックの名前と関数を持つタプル。
    """
    if asyncio.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapped_func() -> None:
            await func(*args, **kwargs)

        return (name, async_wrapped_func)

    @functools.wraps(func)
    async def sync_wrapper() -> None:
        await asyncio.to_thread(func, *args, **kwargs)

    return (name, sync_wrapper)


async def run(
    checks: CheckerEntries,
    output_details: bool = True,
    dedup_window: datetime.timedelta | None = None,
    now: datetime.datetime | None = None,
) -> HealthCheckResult:
    """ヘルスチェックを実行し、結果を返す。

    Args:
        checks: ヘルスチェックの名前と関数のリスト。
        output_details: 詳細を出力するかどうか。デフォルトはTrue。
        dedup_window: ログの重複を防ぐための時間ウィンドウ。デフォルトは1日。
        now: 現在の日時。デフォルトは現在の日時を使用。

    Returns:
        ヘルスチェックの結果。
    """
    if dedup_window is None:
        dedup_window = datetime.timedelta(days=1)
    if now is None:
        now = datetime.datetime.now()
    # 名前の重複はAssertionError
    check_names = [name for name, _ in checks]
    assert len(checks) == len(set(check_names)), f"名前の重複: {check_names}"

    details: dict[str, HealthCheckDetail] = {}

    async def run_check(name: str, func: typing.Callable[[], typing.Awaitable[None]]) -> tuple[str, HealthCheckDetail]:
        start = time.perf_counter()
        try:
            await func()
            elapsed = (time.perf_counter() - start) * 1000
            return name, {"status": "ok", "response_time_ms": int(elapsed)}
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            pytilpack.logging.exception_with_dedup(
                logger,
                e,
                f"Health check failed: {name}",
                dedup_window=dedup_window,
                now=now,
            )
            return name, HealthCheckDetail(
                status="fail",
                response_time_ms=int(elapsed),
                error=f"{e.__class__.__name__}: {e}",
            )

    tasks = [run_check(name, func) for name, func in checks]
    done = await asyncio.gather(*tasks)

    for name, result in done:
        details[name] = result

    uptime = now - startup_time
    overall_status: typing.Literal["ok", "fail"] = "ok" if all(v["status"] == "ok" for v in details.values()) else "fail"

    result = HealthCheckResult(status=overall_status, checked=str(now), uptime=str(uptime))
    if output_details:
        result["details"] = details
    return result
