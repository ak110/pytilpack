"""テストコード。"""

import json
import pathlib

import anthropic
import anthropic.types

import pytilpack.anthropic


def test_gather_events_text():
    """gather_eventsのテスト（テキスト応答）。"""
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

    actual = pytilpack.anthropic.gather_events(chunks, strict=True)
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


def test_gather_events_tool_use():
    """gather_eventsのテスト（ツール使用）。"""
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

    actual = pytilpack.anthropic.gather_events(chunks, strict=True)
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


def test_gather_events_empty():
    """gather_eventsのテスト（空のチャンク）。"""
    actual = pytilpack.anthropic.gather_events([], strict=True)
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


def test_gather_events_text_with_citations():
    """gather_eventsのテスト（テキスト応答 + Citations）。"""
    chunks: list[anthropic.types.RawMessageStreamEvent] = [
        anthropic.types.RawMessageStartEvent(
            type="message_start",
            message=anthropic.types.Message.model_construct(
                id="msg_789",
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
            delta=anthropic.types.TextDelta.model_construct(type="text_delta", text="According to"),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=anthropic.types.TextDelta.model_construct(type="text_delta", text=" the document"),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=anthropic.types.CitationsDelta.model_construct(
                type="citations_delta",
                citation=anthropic.types.CitationPageLocation.model_construct(
                    type="page_location",
                    cited_text="relevant text",
                    document_index=0,
                    start_page_number=1,
                    end_page_number=1,
                ),
            ),
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

    actual = pytilpack.anthropic.gather_events(chunks, strict=True)

    assert isinstance(actual.content[0], anthropic.types.TextBlock)
    assert actual.content[0].text == "According to the document"
    assert actual.content[0].citations is not None
    assert len(actual.content[0].citations) == 1
    assert actual.content[0].citations[0].type == "page_location"
    assert isinstance(actual.content[0].citations[0], anthropic.types.CitationPageLocation)
    assert actual.content[0].citations[0].document_index == 0
    assert actual.content[0].citations[0].start_page_number == 1


def test_gather_events_thinking_with_signature():
    """gather_eventsのテスト（Thinking応答 + Signature）。"""
    chunks: list[anthropic.types.RawMessageStreamEvent] = [
        anthropic.types.RawMessageStartEvent(
            type="message_start",
            message=anthropic.types.Message.model_construct(
                id="msg_abc",
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
            content_block=anthropic.types.ThinkingBlock.model_construct(type="thinking", thinking="", signature=""),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=anthropic.types.ThinkingDelta.model_construct(type="thinking_delta", thinking="Let me think"),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=anthropic.types.ThinkingDelta.model_construct(type="thinking_delta", thinking=" about this"),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=anthropic.types.SignatureDelta.model_construct(type="signature_delta", signature="sig_abc123"),
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
            usage=anthropic.types.MessageDeltaUsage.model_construct(output_tokens=8),
        ),
        anthropic.types.RawMessageStopEvent(type="message_stop"),
    ]

    actual = pytilpack.anthropic.gather_events(chunks, strict=True)

    assert isinstance(actual.content[0], anthropic.types.ThinkingBlock)
    assert actual.content[0].thinking == "Let me think about this"
    assert actual.content[0].signature == "sig_abc123"


def test_gather_events_multiple_citations():
    """gather_eventsのテスト（複数のCitations）。"""
    chunks: list[anthropic.types.RawMessageStreamEvent] = [
        anthropic.types.RawMessageStartEvent(
            type="message_start",
            message=anthropic.types.Message.model_construct(
                id="msg_def",
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
            delta=anthropic.types.TextDelta.model_construct(type="text_delta", text="Based on sources"),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=anthropic.types.CitationsDelta.model_construct(
                type="citations_delta",
                citation=anthropic.types.CitationPageLocation.model_construct(
                    type="page_location",
                    cited_text="relevant text",
                    document_index=0,
                    start_page_number=1,
                    end_page_number=1,
                ),
            ),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=anthropic.types.TextDelta.model_construct(type="text_delta", text=" and references"),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=anthropic.types.CitationsDelta.model_construct(
                type="citations_delta",
                citation=anthropic.types.CitationPageLocation.model_construct(
                    type="page_location",
                    cited_text="another text",
                    document_index=1,
                    start_page_number=2,
                    end_page_number=2,
                ),
            ),
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
            usage=anthropic.types.MessageDeltaUsage.model_construct(output_tokens=6),
        ),
        anthropic.types.RawMessageStopEvent(type="message_stop"),
    ]

    actual = pytilpack.anthropic.gather_events(chunks, strict=True)

    assert isinstance(actual.content[0], anthropic.types.TextBlock)
    assert actual.content[0].text == "Based on sources and references"
    assert actual.content[0].citations is not None
    assert len(actual.content[0].citations) == 2
    assert isinstance(actual.content[0].citations[0], anthropic.types.CitationPageLocation)
    assert actual.content[0].citations[0].document_index == 0
    assert actual.content[0].citations[0].start_page_number == 1
    assert isinstance(actual.content[0].citations[1], anthropic.types.CitationPageLocation)
    assert actual.content[0].citations[1].document_index == 1
    assert actual.content[0].citations[1].start_page_number == 2


def test_gather_events_mixed_blocks():
    """gather_eventsのテスト（複数の異なるContentBlock）。"""
    chunks: list[anthropic.types.RawMessageStreamEvent] = [
        anthropic.types.RawMessageStartEvent(
            type="message_start",
            message=anthropic.types.Message.model_construct(
                id="msg_ghi",
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
        # index=0: ThinkingBlock with signature
        anthropic.types.RawContentBlockStartEvent(
            type="content_block_start",
            index=0,
            content_block=anthropic.types.ThinkingBlock.model_construct(type="thinking", thinking="", signature=""),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=anthropic.types.ThinkingDelta.model_construct(type="thinking_delta", thinking="Thinking..."),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=anthropic.types.SignatureDelta.model_construct(type="signature_delta", signature="sig_xyz"),
        ),
        anthropic.types.RawContentBlockStopEvent(type="content_block_stop", index=0),
        # index=1: TextBlock with citations
        anthropic.types.RawContentBlockStartEvent(
            type="content_block_start",
            index=1,
            content_block=anthropic.types.TextBlock.model_construct(type="text", text=""),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=1,
            delta=anthropic.types.TextDelta.model_construct(type="text_delta", text="Answer"),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=1,
            delta=anthropic.types.CitationsDelta.model_construct(
                type="citations_delta",
                citation=anthropic.types.CitationPageLocation.model_construct(
                    type="page_location",
                    cited_text="more text",
                    document_index=2,
                    start_page_number=3,
                    end_page_number=3,
                ),
            ),
        ),
        anthropic.types.RawContentBlockStopEvent(type="content_block_stop", index=1),
        # index=2: ToolUseBlock
        anthropic.types.RawContentBlockStartEvent(
            type="content_block_start",
            index=2,
            content_block=anthropic.types.ToolUseBlock.model_construct(
                type="tool_use",
                id="toolu_999",
                name="search",
                input={},
            ),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=2,
            delta=anthropic.types.InputJSONDelta.model_construct(type="input_json_delta", partial_json='{"query"'),
        ),
        anthropic.types.RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=2,
            delta=anthropic.types.InputJSONDelta.model_construct(type="input_json_delta", partial_json=':"test"}'),
        ),
        anthropic.types.RawContentBlockStopEvent(type="content_block_stop", index=2),
        anthropic.types.RawMessageDeltaEvent(
            type="message_delta",
            delta=anthropic.types.raw_message_delta_event.Delta.model_construct(
                stop_reason="tool_use",
                stop_sequence=None,
            ),
            usage=anthropic.types.MessageDeltaUsage.model_construct(output_tokens=20),
        ),
        anthropic.types.RawMessageStopEvent(type="message_stop"),
    ]

    actual = pytilpack.anthropic.gather_events(chunks, strict=True)

    assert len(actual.content) == 3
    # index=0: ThinkingBlock
    assert isinstance(actual.content[0], anthropic.types.ThinkingBlock)
    assert actual.content[0].type == "thinking"
    assert actual.content[0].thinking == "Thinking..."
    assert actual.content[0].signature == "sig_xyz"
    # index=1: TextBlock
    assert isinstance(actual.content[1], anthropic.types.TextBlock)
    assert actual.content[1].type == "text"
    assert actual.content[1].text == "Answer"
    assert actual.content[1].citations is not None
    assert len(actual.content[1].citations) == 1
    # index=2: ToolUseBlock
    assert isinstance(actual.content[2], anthropic.types.ToolUseBlock)
    assert actual.content[2].type == "tool_use"
    assert actual.content[2].id == "toolu_999"
    assert actual.content[2].name == "search"
    assert actual.content[2].input == {"query": "test"}


def test_gather_events_from_files() -> None:
    """gather_eventsのテスト（JSONLファイルとJSONファイルを使用）。"""
    # テストデータディレクトリのパス
    data_dir = pathlib.Path(__file__).parent / "data"
    events_file = data_dir / "messages-events.jsonl"
    expected_file = data_dir / "messages-events-response.json"

    # JSONLファイルからイベントを読み込み
    events: list[anthropic.types.RawMessageStreamEvent] = []
    for line in events_file.read_text(encoding="utf-8").strip().splitlines():
        event_dict = json.loads(line)
        # 各イベントのtypeに応じて適切なクラスにパース
        event_type = event_dict.get("type")
        if event_type == "message_start":
            events.append(anthropic.types.RawMessageStartEvent.model_validate(event_dict))
        elif event_type == "content_block_start":
            events.append(anthropic.types.RawContentBlockStartEvent.model_validate(event_dict))
        elif event_type == "content_block_delta":
            events.append(anthropic.types.RawContentBlockDeltaEvent.model_validate(event_dict))
        elif event_type == "content_block_stop":
            events.append(anthropic.types.RawContentBlockStopEvent.model_validate(event_dict))
        elif event_type == "message_delta":
            events.append(anthropic.types.RawMessageDeltaEvent.model_validate(event_dict))
        elif event_type == "message_stop":
            events.append(anthropic.types.RawMessageStopEvent.model_validate(event_dict))
        else:
            raise ValueError(f"Unknown event type: {event_dict}")

    # gather_eventsを実行
    actual = pytilpack.anthropic.gather_events(events, strict=True)

    # 期待される結果を読み込み
    expected_dict = json.loads(expected_file.read_text(encoding="utf-8"))

    # 結果を比較
    assert actual.model_dump() == expected_dict
