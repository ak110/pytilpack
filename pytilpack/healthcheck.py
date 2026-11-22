__lazy_modules__ = ["asyncio", "datetime", "functools", "inspect", "logging", "pytilpack.logging", "time", "typing"]

import asyncio
import datetime as dt
import functools
import inspect
import logging
import time
import typing

import pytilpack.logging

CheckerType = typing.Callable[[], typing.Awaitable[None]]

CheckerEntry = tuple[str, CheckerType]

CheckerEntries = list[CheckerEntry]

startup_time = dt.datetime.now()

logger = logging.getLogger(__name__)


class HealthCheckDetail(typing.TypedDict):
    status: typing.Literal["ok", "fail"]
    response_time_ms: float
    error: typing.NotRequired[str]


class HealthCheckResult(typing.TypedDict):
    status: typing.Literal["ok", "fail"]
    checked: str
    uptime: str
    details: typing.NotRequired[dict[str, HealthCheckDetail]]


def make_entry[**P, R](
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
    if inspect.iscoroutinefunction(func):

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
    dedup_window: dt.timedelta | None = None,
    now: dt.datetime | None = None,
    start_time: dt.datetime | None = None,
) -> HealthCheckResult:
    if dedup_window is None:
        dedup_window = dt.timedelta(days=1)
    if now is None:
        now = dt.datetime.now()
    if start_time is None:
        start_time = startup_time
    check_names = [name for name, _ in checks]
    assert len(checks) == len(set(check_names)), f"ヘルスチェック名が重複しています: {check_names}"

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

    uptime = now - start_time
    overall_status: typing.Literal["ok", "fail"] = "ok" if all(v["status"] == "ok" for v in details.values()) else "fail"

    result = HealthCheckResult(status=overall_status, checked=str(now), uptime=str(uptime))
    if output_details:
        result["details"] = details
    return result
