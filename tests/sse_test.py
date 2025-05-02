"""SSE モジュールのテスト。"""

import asyncio
import typing

import pytest

import pytilpack.sse


def test_sse_simple():
    """シンプルなメッセージ。"""
    msg = pytilpack.sse.SSE("test data")
    assert msg.to_str() == "data: test data\n\n"


def test_sse_multiline():
    """複数行データ。"""
    msg = pytilpack.sse.SSE("line 1\nline 2\nline 3")
    assert msg.to_str() == "data: line 1\ndata: line 2\ndata: line 3\n\n"


def test_sse_all_fields():
    """全フィールドを使用したケース。"""
    msg = pytilpack.sse.SSE(data="test data", event="update", id="123", retry=3000)
    assert msg.to_str() == "event: update\nid: 123\nretry: 3000\ndata: test data\n\n"


@pytest.mark.asyncio
async def test_generator_str():
    """文字列のキープアライブ。"""

    @pytilpack.sse.generator(interval=0.15)
    async def generate() -> typing.AsyncIterator[str]:
        yield "data: msg1\n\n"
        await asyncio.sleep(0.1)  # 短い間隔
        yield "data: msg2\n\n"
        await asyncio.sleep(0.2)  # もう少し長い間隔
        yield "data: msg3\n\n"

    # キープアライブを0.15秒間隔に設定
    messages = []
    async for msg in generate():
        messages.append(msg)

    assert len(messages) == 4
    assert messages[0] == "data: msg1\n\n"
    assert messages[1] == "data: msg2\n\n"
    assert messages[2] == ": ping\n\n"
    assert messages[3] == "data: msg3\n\n"


@pytest.mark.asyncio
async def test_generator_sse():
    """SSEオブジェクトのキープアライブ。"""

    @pytilpack.sse.generator(interval=0.15)
    async def generate() -> typing.AsyncIterator[pytilpack.sse.SSE]:
        yield pytilpack.sse.SSE("msg1")
        await asyncio.sleep(0.1)  # 短い間隔
        yield pytilpack.sse.SSE("msg2", event="update")
        await asyncio.sleep(0.2)  # もう少し長い間隔
        yield pytilpack.sse.SSE("msg3", id="123")

    messages = []
    async for msg in generate():
        messages.append(msg)

    assert len(messages) == 4
    assert messages[0] == "data: msg1\n\n"
    assert messages[1] == "event: update\ndata: msg2\n\n"
    assert messages[2] == ": ping\n\n"
    assert messages[3] == "id: 123\ndata: msg3\n\n"


@pytest.mark.asyncio
async def test_generator_mixed():
    """文字列とSSEオブジェクトの混合。"""

    @pytilpack.sse.generator(interval=0.15)
    async def generate() -> typing.AsyncIterator[str | pytilpack.sse.SSE]:
        yield "data: raw1\n\n"
        await asyncio.sleep(0.1)
        yield pytilpack.sse.SSE("msg1", event="update")
        await asyncio.sleep(0.2)
        yield "data: raw2\n\n"

    messages = []
    async for msg in generate():
        messages.append(msg)

    assert len(messages) == 4
    assert messages[0] == "data: raw1\n\n"
    assert messages[1] == "event: update\ndata: msg1\n\n"
    assert messages[2] == ": ping\n\n"
    assert messages[3] == "data: raw2\n\n"
