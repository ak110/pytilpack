"""SSE モジュールのテスト。"""

import asyncio

import pytest

import pytilpack.sse


def test_sse_simple():
    """シンプルなメッセージのシリアライズをテスト。"""
    msg = pytilpack.sse.SSE("test data")
    assert msg.serialize() == "data: test data\n\n"


def test_sse_multiline():
    """複数行データのシリアライズをテスト。"""
    msg = pytilpack.sse.SSE("line 1\nline 2\nline 3")
    assert msg.serialize() == "data: line 1\ndata: line 2\ndata: line 3\n\n"


def test_sse_all_fields():
    """全フィールドを使用したケースをテスト。"""
    msg = pytilpack.sse.SSE(data="test data", event="update", id="123", retry=3000)
    assert msg.serialize() == "event: update\nid: 123\nretry: 3000\ndata: test data\n\n"


@pytest.mark.asyncio
async def test_add_keepalive():
    """キープアライブの追加をテスト。"""

    async def generate():
        yield "data: msg1\n\n"
        await asyncio.sleep(0.1)  # 短い間隔
        yield "data: msg2\n\n"
        await asyncio.sleep(0.2)  # もう少し長い間隔
        yield "data: msg3\n\n"

    # キープアライブを0.15秒間隔に設定
    messages = []
    async for msg in pytilpack.sse.add_keepalive(generate(), interval=0.15):
        messages.append(msg)

    assert len(messages) == 4
    assert messages[0] == "data: msg1\n\n"
    assert messages[1] == "data: msg2\n\n"
    assert messages[2] == ": ping\n\n"
    assert messages[3] == "data: msg3\n\n"
