"""SSE モジュールのテスト。"""

import asyncio
import typing

import pytest

import pytilpack.sse


def test_sse_to_str() -> None:
    """SSE.to_str()の各種パターンテスト。"""
    # シンプルなメッセージ
    assert pytilpack.sse.SSE("test data").to_str() == "data: test data\n\n"

    # 複数行データ (LF / CRLF / CR)
    assert pytilpack.sse.SSE("line 1\nline 2\nline 3").to_str() == "data: line 1\ndata: line 2\ndata: line 3\n\n"
    assert pytilpack.sse.SSE("line 1\r\nline 2\r\nline 3").to_str() == "data: line 1\ndata: line 2\ndata: line 3\n\n"
    assert pytilpack.sse.SSE("line 1\rline 2\rline 3").to_str() == "data: line 1\ndata: line 2\ndata: line 3\n\n"

    # 全フィールドを使用したケース
    msg = pytilpack.sse.SSE(data="test data", event="update", id="123", retry=3000)
    assert msg.to_str() == "event: update\nid: 123\nretry: 3000\ndata: test data\n\n"


@pytest.mark.parametrize(
    "sep",
    ["\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"],
)
def test_sse_non_sse_line_separators_not_split(sep: str) -> None:
    """SSE仕様外の行区切り文字で分割されないことを確認。"""
    data = f"before{sep}after"
    msg = pytilpack.sse.SSE(data)
    assert msg.to_str() == f"data: before{sep}after\n\n"


@pytest.mark.asyncio
async def test_generator() -> None:
    """generatorデコレーターのキープアライブ（文字列・SSE・混合）テスト。"""

    # 文字列のキープアライブ
    @pytilpack.sse.generator(interval=0.15)
    async def generate_str() -> typing.AsyncGenerator[str, None]:
        yield "data: msg1\n\n"
        await asyncio.sleep(0.1)
        yield "data: msg2\n\n"
        await asyncio.sleep(0.2)
        yield "data: msg3\n\n"

    messages: list[str] = []
    async for msg in generate_str():
        messages.append(msg)

    assert len(messages) == 4
    assert messages[0] == "data: msg1\n\n"
    assert messages[1] == "data: msg2\n\n"
    assert messages[2] == ": ping\n\n"
    assert messages[3] == "data: msg3\n\n"

    # SSEオブジェクトのキープアライブ
    @pytilpack.sse.generator(interval=0.15)
    async def generate_sse() -> typing.AsyncGenerator[pytilpack.sse.SSE, None]:
        yield pytilpack.sse.SSE("msg1")
        await asyncio.sleep(0.1)
        yield pytilpack.sse.SSE("msg2", event="update")
        await asyncio.sleep(0.2)
        yield pytilpack.sse.SSE("msg3", id="123")

    messages_sse: list[typing.Any] = []
    async for msg in generate_sse():
        messages_sse.append(msg)

    assert len(messages_sse) == 4
    assert messages_sse[0] == "data: msg1\n\n"
    assert messages_sse[1] == "event: update\ndata: msg2\n\n"
    assert messages_sse[2] == ": ping\n\n"
    assert messages_sse[3] == "id: 123\ndata: msg3\n\n"

    # 文字列とSSEオブジェクトの混合
    @pytilpack.sse.generator(interval=0.15)
    async def generate_mixed() -> typing.AsyncGenerator[str | pytilpack.sse.SSE, None]:
        yield "data: raw1\n\n"
        await asyncio.sleep(0.1)
        yield pytilpack.sse.SSE("msg1", event="update")
        await asyncio.sleep(0.2)
        yield "data: raw2\n\n"

    messages_mixed: list[typing.Any] = []
    async for msg in generate_mixed():
        messages_mixed.append(msg)

    assert len(messages_mixed) == 4
    assert messages_mixed[0] == "data: raw1\n\n"
    assert messages_mixed[1] == "event: update\ndata: msg1\n\n"
    assert messages_mixed[2] == ": ping\n\n"
    assert messages_mixed[3] == "data: raw2\n\n"


@pytest.mark.asyncio
async def test_generator_cancel() -> None:
    """キャンセルのテスト。"""
    cleanup_called = False

    @pytilpack.sse.generator(interval=0.15)
    async def generate() -> typing.AsyncGenerator[str, None]:
        nonlocal cleanup_called
        try:
            yield "data: msg1\n\n"
            await asyncio.sleep(1.0)  # 長い待機（キャンセルされる）
            yield "data: msg2\n\n"
        finally:
            cleanup_called = True

    messages: list[str] = []
    gen = generate()
    async for msg in gen:
        messages.append(msg)
        if len(messages) == 1:
            # 最初のメッセージ受信後にキャンセル
            await gen.aclose()
            break

    assert messages == ["data: msg1\n\n"]
    assert cleanup_called
