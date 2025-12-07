"""テストコード。"""

import anthropic
import anthropic.types

import pytilpack.anthropic


def test_gather_chunks_text():
    """gather_chunksのテスト（テキスト応答）。"""
    chunks: list[anthropic.types.RawMessageStreamEvent] = [
        anthropic.types.RawMessageStartEvent(
            type="message_start",
            message=anthropic.types.Message.model_construct(
                id="msg_123",
                type="message",
                role="assistant",
                content=[],
                model="claude-3-5-sonnet-20241022",
                stop_reason=None,
                stop_sequence=None,
                usage=anthropic.types.Usage.model_construct(
                    input_tokens=10,
                    output_tokens=0,
                ),
            ),
        ),
        anthropic.types.RawContentBlockStartEvent(
            type="content_block_start",
            index=0,
            content_block=anthropic.types.TextBlock.model_construct(type="text", text=""),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=anthropic.types.TextDelta.model_construct(type="text_delta", text="Hello"),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=anthropic.types.TextDelta.model_construct(type="text_delta", text=" world"),
        ),
        anthropic.types.RawContentBlockStopEvent(
            type="content_block_stop",
            index=0,
        ),
        anthropic.types.RawMessageDeltaEvent(
            type="message_delta",
            delta=anthropic.types.raw_message_delta_event.Delta.model_construct(
                stop_reason="end_turn",
                stop_sequence=None,
            ),
            usage=anthropic.types.MessageDeltaUsage.model_construct(output_tokens=5),
        ),
        anthropic.types.RawMessageStopEvent(type="message_stop"),
    ]

    actual = pytilpack.anthropic.gather_chunks(chunks, strict=True)
    expected = anthropic.types.Message.model_construct(
        id="msg_123",
        type="message",
        role="assistant",
        content=[anthropic.types.TextBlock.model_construct(type="text", text="Hello world")],
        model="claude-3-5-sonnet-20241022",
        stop_reason="end_turn",
        stop_sequence=None,
        usage=anthropic.types.Usage.model_construct(
            input_tokens=10,
            output_tokens=5,
        ),
    )
    assert actual.model_dump() == expected.model_dump()


def test_gather_chunks_tool_use():
    """gather_chunksのテスト（ツール使用）。"""
    chunks: list[anthropic.types.RawMessageStreamEvent] = [
        anthropic.types.RawMessageStartEvent(
            type="message_start",
            message=anthropic.types.Message.model_construct(
                id="msg_456",
                type="message",
                role="assistant",
                content=[],
                model="claude-3-5-sonnet-20241022",
                stop_reason=None,
                stop_sequence=None,
                usage=anthropic.types.Usage.model_construct(
                    input_tokens=20,
                    output_tokens=0,
                ),
            ),
        ),
        anthropic.types.RawContentBlockStartEvent(
            type="content_block_start",
            index=0,
            content_block=anthropic.types.ToolUseBlock.model_construct(
                type="tool_use",
                id="toolu_123",
                name="calculator",
                input={},
            ),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=anthropic.types.InputJSONDelta.model_construct(type="input_json_delta", partial_json='{"expre'),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=anthropic.types.InputJSONDelta.model_construct(type="input_json_delta", partial_json='ssion":"1+1"}'),
        ),
        anthropic.types.RawContentBlockStopEvent(
            type="content_block_stop",
            index=0,
        ),
        anthropic.types.RawMessageDeltaEvent(
            type="message_delta",
            delta=anthropic.types.raw_message_delta_event.Delta.model_construct(
                stop_reason="tool_use",
                stop_sequence=None,
            ),
            usage=anthropic.types.MessageDeltaUsage.model_construct(output_tokens=15),
        ),
        anthropic.types.RawMessageStopEvent(type="message_stop"),
    ]

    actual = pytilpack.anthropic.gather_chunks(chunks, strict=True)
    expected = anthropic.types.Message.model_construct(
        id="msg_456",
        type="message",
        role="assistant",
        content=[
            anthropic.types.ToolUseBlock.model_construct(
                type="tool_use",
                id="toolu_123",
                name="calculator",
                input={"expression": "1+1"},
            )
        ],
        model="claude-3-5-sonnet-20241022",
        stop_reason="tool_use",
        stop_sequence=None,
        usage=anthropic.types.Usage.model_construct(
            input_tokens=20,
            output_tokens=15,
        ),
    )
    assert actual.model_dump() == expected.model_dump()


def test_gather_chunks_empty():
    """gather_chunksのテスト（空のチャンク）。"""
    actual = pytilpack.anthropic.gather_chunks([], strict=True)
    expected = anthropic.types.Message.model_construct(
        id="",
        type="message",
        role="assistant",
        content=[],
        model="",
        stop_reason=None,
        stop_sequence=None,
        usage=anthropic.types.Usage.model_construct(input_tokens=0, output_tokens=0),
    )
    assert actual.model_dump() == expected.model_dump()
