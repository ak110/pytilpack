import asyncio
import contextlib
import typing

import pytest

import pytilpack.sse


def test_sse_to_str() -> None:
    assert pytilpack.sse.SSE("test data").to_str() == "data: test data\n\n"

    assert pytilpack.sse.SSE("line 1\nline 2\nline 3").to_str() == "data: line 1\ndata: line 2\ndata: line 3\n\n"
    assert pytilpack.sse.SSE("line 1\r\nline 2\r\nline 3").to_str() == "data: line 1\ndata: line 2\ndata: line 3\n\n"
    assert pytilpack.sse.SSE("line 1\rline 2\rline 3").to_str() == "data: line 1\ndata: line 2\ndata: line 3\n\n"

    msg = pytilpack.sse.SSE(data="test data", event="update", id="123", retry=3000)
    assert msg.to_str() == "event: update\nid: 123\nretry: 3000\ndata: test data\n\n"


def test_sse_comment() -> None:
    assert pytilpack.sse.SSE(comment="ping").to_str() == ": ping\n\n"

    assert pytilpack.sse.SSE(data="x", comment="info").to_str() == ": info\ndata: x\n\n"

    msg = pytilpack.sse.SSE(data="x", event="e", id="1", retry=3000, comment="c")
    assert msg.to_str() == "event: e\nid: 1\nretry: 3000\n: c\ndata: x\n\n"

    assert pytilpack.sse.SSE(comment="a\nb\r\nc\rd").to_str() == ": a\n: b\n: c\n: d\n\n"


def test_sse_requires_data_or_comment() -> None:
    with pytest.raises(ValueError):
        pytilpack.sse.SSE()
    with pytest.raises(ValueError):
        pytilpack.sse.SSE(event="e")


@pytest.mark.parametrize(
    "sep",
    ["\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", " ", " "],
)
def test_sse_non_sse_line_separators_not_split(sep: str) -> None:
    data = f"before{sep}after"
    msg = pytilpack.sse.SSE(data)
    assert msg.to_str() == f"data: before{sep}after\n\n"


@pytest.mark.asyncio
async def test_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    waiting = asyncio.Event()
    release = asyncio.Event()
    original_wait_for = asyncio.wait_for
    waits = 0

    async def wait_for(awaitable: typing.Any, timeout: float) -> typing.Any:
        nonlocal waits
        waits += 1
        assert 50 < timeout <= 60
        if waits == 2:
            await original_wait_for(waiting.wait(), timeout=5)
            awaitable.cancel()
            raise TimeoutError
        return await original_wait_for(awaitable, timeout=5)

    monkeypatch.setattr(pytilpack.sse.asyncio, "wait_for", wait_for)

    @pytilpack.sse.generator(interval=60)
    async def generate() -> typing.AsyncGenerator[str | pytilpack.sse.SSE, None]:
        yield "data: raw"
        waiting.set()
        await original_wait_for(release.wait(), timeout=5)
        yield pytilpack.sse.SSE("updated", event="update", id="123")

    async with contextlib.aclosing(generate()) as messages:
        assert await original_wait_for(anext(messages), timeout=5) == "data: raw\n\n"
        assert await original_wait_for(anext(messages), timeout=5) == ": ping\n\n"
        release.set()
        assert await original_wait_for(anext(messages), timeout=5) == "event: update\nid: 123\ndata: updated\n\n"
        with pytest.raises(StopAsyncIteration):
            await original_wait_for(anext(messages), timeout=5)


@pytest.mark.asyncio
async def test_generator_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    cleanup_called = False
    cancelled = False
    waiting = asyncio.Event()
    release = asyncio.Event()
    original_wait_for = asyncio.wait_for
    waits = 0

    async def wait_for(awaitable: typing.Any, timeout: float, **kwargs: typing.Any) -> typing.Any:
        del kwargs
        nonlocal waits
        waits += 1
        if waits > 1:
            await original_wait_for(waiting.wait(), timeout=5)
            raise TimeoutError
        return await original_wait_for(awaitable, timeout=timeout)

    monkeypatch.setattr(pytilpack.sse.asyncio, "wait_for", wait_for)

    @pytilpack.sse.generator(interval=0.15)
    async def generate() -> typing.AsyncGenerator[str, None]:
        nonlocal cleanup_called, cancelled
        try:
            yield "data: msg1\n\n"
            waiting.set()
            await release.wait()
            yield "data: msg2\n\n"
        except asyncio.CancelledError:
            cancelled = True
            raise
        finally:
            cleanup_called = True

    gen = generate()
    assert await anext(gen) == "data: msg1\n\n"
    next_message = asyncio.create_task(anext(gen))
    await original_wait_for(waiting.wait(), timeout=5)
    assert await original_wait_for(next_message, timeout=5) == ": ping\n\n"
    close_task = asyncio.create_task(gen.aclose())
    try:
        await asyncio.wait({close_task}, timeout=1)
        assert cancelled
    finally:
        release.set()
        with contextlib.suppress(asyncio.CancelledError):
            await original_wait_for(close_task, timeout=5)
    assert cleanup_called
