"""ヘルスチェック機能の実装用ヘルパー。"""

import asyncio
import datetime
import logging
import time
import typing

import pytilpack.logging_

CheckerType = typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, None]]
"""ヘルスチェック関数の型。"""

CheckerEntry = tuple[str, CheckerType]
"""ヘルスチェックの名前と関数を持つタプル。"""

startup_time = datetime.datetime.now()
"""アプリケーションの起動時間を記録する変数。ヘルスチェックの uptime に使用される。"""

logger = logging.getLogger(__name__)


class HealthCheckDetail(typing.TypedDict):
    """ヘルスチェックの詳細を表す型。"""

    status: typing.Literal["ok", "fail"]
    response_time_ms: float
    error: str | None


class HealthCheckResult(typing.TypedDict):
    """ヘルスチェックの結果を表す型。"""

    status: typing.Literal["ok", "fail"]
    checked: str
    uptime: str
    details: typing.NotRequired[dict[str, HealthCheckDetail]]


async def run(
    checks: list[CheckerEntry],
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

    async def run_check(
        name: str, func: typing.Callable[[], typing.Awaitable[None]]
    ) -> tuple[str, HealthCheckDetail]:
        start = time.perf_counter()
        try:
            await func()
            elapsed = (time.perf_counter() - start) * 1000
            return name, {
                "status": "ok",
                "response_time_ms": int(elapsed),
                "error": None,
            }
        except Exception as e:
            pytilpack.logging_.exception_with_dedup(
                logger,
                e,
                f"Health check failed: {name}",
                dedup_window=dedup_window,
                now=now,
            )
            elapsed = (time.perf_counter() - start) * 1000
            return name, {
                "status": "fail",
                "response_time_ms": int(elapsed),
                "error": str(e),
            }

    tasks = [run_check(name, func) for name, func in checks]
    done = await asyncio.gather(*tasks)

    for name, result in done:
        details[name] = result

    uptime = now - startup_time
    overall_status: typing.Literal["ok", "fail"] = (
        "ok" if all(v["status"] == "ok" for v in details.values()) else "fail"
    )

    result: HealthCheckResult = {
        "status": overall_status,
        "checked": str(now),
        "uptime": str(uptime),
    }
    if output_details:
        result["details"] = details
    return result
