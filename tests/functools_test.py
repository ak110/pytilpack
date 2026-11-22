import logging
import types
import typing

import pytest
import requests

import pytilpack.functools


@pytest.mark.asyncio
async def test_retry() -> None:
    call_count = 0

    @pytilpack.functools.retry(2, initial_delay=0, exponential_base=0)
    def f_sync():
        nonlocal call_count
        call_count += 1

    f_sync()
    assert call_count == 1

    call_count = 0

    @pytilpack.functools.retry(2, initial_delay=0, exponential_base=0)
    def f_sync_err():
        nonlocal call_count
        call_count += 1
        raise RuntimeError("test")

    with pytest.raises(RuntimeError):
        f_sync_err()
    assert call_count == 3

    call_count = 0

    @pytilpack.functools.retry(2, initial_delay=0, exponential_base=0)
    async def f_async():
        nonlocal call_count
        call_count += 1

    await f_async()
    assert call_count == 1

    call_count = 0

    @pytilpack.functools.retry(2, initial_delay=0, exponential_base=0)
    async def f_async_err():
        nonlocal call_count
        call_count += 1
        raise RuntimeError("test")

    with pytest.raises(RuntimeError):
        await f_async_err()
    assert call_count == 3


class _StatusCodeError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"status_code={status_code}")
        self.status_code = status_code


@pytest.mark.asyncio
async def test_retry_default_status_codes() -> None:
    call_count = 0

    @pytilpack.functools.retry(max_retries=2, initial_delay=0, exponential_base=0)
    def f_sync(status_code: int):
        nonlocal call_count
        call_count += 1
        raise _StatusCodeError(status_code)

    @pytilpack.functools.retry(max_retries=2, initial_delay=0, exponential_base=0)
    async def f_async(status_code: int):
        nonlocal call_count
        call_count += 1
        raise _StatusCodeError(status_code)

    for status_code in (408, 429, 500, 502, 503, 504, 529):
        call_count = 0
        with pytest.raises(_StatusCodeError):
            f_sync(status_code)
        assert call_count == 3, f"sync: status_code={status_code}"

        call_count = 0
        with pytest.raises(_StatusCodeError):
            await f_async(status_code)
        assert call_count == 3, f"async: status_code={status_code}"

    call_count = 0
    with pytest.raises(_StatusCodeError):
        f_sync(404)
    assert call_count == 1

    call_count = 0
    with pytest.raises(_StatusCodeError):
        await f_async(404)
    assert call_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("duration", [0.124, 0.125])
@pytest.mark.parametrize("is_async", [False, True], ids=["sync", "async"])
async def test_warn_if_slow(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, duration: float, is_async: bool
) -> None:
    ticks = iter((0.0, duration))
    monkeypatch.setattr(pytilpack.functools, "time", types.SimpleNamespace(perf_counter=lambda: next(ticks)))

    @pytilpack.functools.warn_if_slow(threshold_seconds=0.125)
    def sync_call(x: int, *, label: str) -> str:
        return f"{x}-{label}"

    @pytilpack.functools.warn_if_slow(threshold_seconds=0.125)
    async def async_call(x: int, *, label: str) -> str:
        return f"{x}-{label}"

    with caplog.at_level(logging.WARNING):
        result = await async_call(42, label="test") if is_async else sync_call(42, label="test")
    assert result == "42-test"
    if duration < 0.125:
        assert not caplog.records
    else:
        assert len(caplog.records) == 1
        (record,) = caplog.records
        assert record.levelno == logging.WARNING
        assert ("async_call" if is_async else "sync_call") in record.getMessage()


@pytest.mark.asyncio
async def test_retry_override() -> None:
    call_count = 0

    @pytilpack.functools.retry(max_retries=5, initial_delay=0, exponential_base=0)
    def f(retry=None):
        del retry  # noqa
        nonlocal call_count
        call_count += 1
        raise RuntimeError("test")

    with pytest.raises(RuntimeError):
        f()
    assert call_count == 6

    call_count = 0
    with pytest.raises(RuntimeError):
        f(retry=pytilpack.functools.Retry(max_retries=2))
    assert call_count == 3

    call_count = 0
    with pytest.raises(RuntimeError):
        f(retry=pytilpack.functools.Retry(max_retries=1))
    assert call_count == 2

    call_count = 0

    @pytilpack.functools.retry(max_retries=5, initial_delay=0, exponential_base=0)
    async def f_async(retry=None):
        del retry  # noqa
        nonlocal call_count
        call_count += 1
        raise RuntimeError("test")

    with pytest.raises(RuntimeError):
        await f_async()
    assert call_count == 6

    call_count = 0
    with pytest.raises(RuntimeError):
        await f_async(retry=pytilpack.functools.Retry(max_retries=2))
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_should_retry() -> None:

    def should_retry_func(exc: Exception) -> bool:
        return isinstance(exc, ValueError)

    call_count = 0

    @pytilpack.functools.retry(max_retries=3, initial_delay=0, exponential_base=0, should_retry=should_retry_func)
    def f(error_type: type[Exception]):
        nonlocal call_count
        call_count += 1
        raise error_type("test")

    call_count = 0
    with pytest.raises(ValueError):
        f(ValueError)
    assert call_count == 4

    call_count = 0
    with pytest.raises(RuntimeError):
        f(RuntimeError)
    assert call_count == 1

    @pytilpack.functools.retry(max_retries=3, initial_delay=0, exponential_base=0, should_retry=should_retry_func)
    async def f_async(error_type: type[Exception]):
        nonlocal call_count
        call_count += 1
        raise error_type("test")

    call_count = 0
    with pytest.raises(ValueError):
        await f_async(ValueError)
    assert call_count == 4

    call_count = 0
    with pytest.raises(RuntimeError):
        await f_async(RuntimeError)
    assert call_count == 1


@pytest.mark.parametrize("is_async", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
@pytest.mark.parametrize("retry_after,expected_waits", [(1, [1, 1, 1]), (2, [2, 2])])
async def test_retry_override_total_delay(
    monkeypatch: pytest.MonkeyPatch, is_async: bool, retry_after: int, expected_waits: list[int]
) -> None:

    waits: list[float] = []

    def sleep(delay: float, **kwargs: typing.Any) -> None:
        del kwargs
        waits.append(delay)

    async def async_sleep(delay: float, **kwargs: typing.Any) -> None:
        del kwargs
        waits.append(delay)

    monkeypatch.setattr(pytilpack.functools.time, "sleep", sleep)
    monkeypatch.setattr(pytilpack.functools.asyncio, "sleep", async_sleep)
    response = requests.Response()
    response.status_code = 429
    response.headers["Retry-After"] = str(retry_after)
    call_count = 0

    @pytilpack.functools.retry(max_retries=1, initial_delay=1, exponential_base=1)
    def f_sync(retry=None):
        del retry  # noqa
        nonlocal call_count
        call_count += 1
        raise requests.HTTPError(response=response)

    @pytilpack.functools.retry(max_retries=1, initial_delay=1, exponential_base=1)
    async def f_async(retry=None):
        del retry  # noqa
        nonlocal call_count
        call_count += 1
        raise requests.HTTPError(response=response)

    with pytest.raises(requests.HTTPError):
        if is_async:
            await f_async(retry=pytilpack.functools.Retry(max_retries=3))
        else:
            f_sync(retry=pytilpack.functools.Retry(max_retries=3))
    assert call_count == len(expected_waits) + 1
    assert waits == expected_waits


def test_retry_override_should_retry() -> None:
    call_count = 0

    @pytilpack.functools.retry(max_retries=3, initial_delay=0, exponential_base=0)
    def f(retry=None, error_type: type[Exception] = RuntimeError):
        del retry  # noqa
        nonlocal call_count
        call_count += 1
        raise error_type("test")

    with pytest.raises(RuntimeError):
        f()
    assert call_count == 4

    def custom_should_retry(exc: Exception) -> bool:
        return isinstance(exc, ValueError)

    call_count = 0
    with pytest.raises(RuntimeError):
        f(retry=pytilpack.functools.Retry(should_retry=custom_should_retry), error_type=RuntimeError)
    assert call_count == 1

    call_count = 0
    with pytest.raises(ValueError):
        f(retry=pytilpack.functools.Retry(should_retry=custom_should_retry), error_type=ValueError)
    assert call_count == 4
