"""Anthropic Python API library用のユーティリティ集。"""

import json
import logging
import typing

import anthropic.types

logger = logging.getLogger(__name__)


def gather_events(
    chunks: typing.Iterable[anthropic.types.RawMessageStreamEvent], strict: bool = False
) -> anthropic.types.Message:
    """ストリーミングのチャンクを結合する。"""
    chunks = list(chunks)
    if len(chunks) == 0:
        return anthropic.types.Message.model_construct(
            id="",
            type="message",
            role="assistant",
            content=[],
            model="",
            stop_reason=None,
            stop_sequence=None,
            usage=anthropic.types.Usage.model_construct(input_tokens=0, output_tokens=0),
        )

    # message_startイベントからベースとなるメッセージを取得
    message_start_events = [c for c in chunks if hasattr(c, "type") and c.type == "message_start" and hasattr(c, "message")]
    if len(message_start_events) == 0:
        raise ValueError("message_start event not found")
    if len(message_start_events) > 1:
        _warn(strict, f"複数のmessage_startイベントが見つかりました: {len(message_start_events)}")

    base_message = message_start_events[0].message

    # content_block_startイベントからcontent blocksを収集
    content_block_start_events = [
        c for c in chunks if hasattr(c, "type") and c.type == "content_block_start" and hasattr(c, "content_block")
    ]

    # 各content blockのindexごとに処理
    if len(content_block_start_events) == 0:
        content_blocks = []
    else:
        min_index = min(e.index for e in content_block_start_events)
        max_index = max(e.index for e in content_block_start_events)
        content_blocks = [_make_content_block(chunks, i, strict) for i in range(min_index, max_index + 1)]

    # message_deltaイベントからstop_reason, stop_sequence, usageを収集
    message_delta_events = [c for c in chunks if hasattr(c, "type") and c.type == "message_delta" and hasattr(c, "delta")]

    stop_reason = None
    stop_sequence = None
    if len(message_delta_events) > 0:
        stop_reasons = [e.delta.stop_reason for e in message_delta_events if e.delta.stop_reason is not None]
        if len(stop_reasons) > 0:
            stop_reason = _equals_all_get(strict, "stop_reason", stop_reasons)

        stop_sequences = [e.delta.stop_sequence for e in message_delta_events if e.delta.stop_sequence is not None]
        if len(stop_sequences) > 0:
            stop_sequence = _equals_all_get(strict, "stop_sequence", stop_sequences)

    # usageの集計
    usage = _aggregate_usage(chunks, strict)

    # Messageオブジェクトを構築
    message = anthropic.types.Message.model_construct(
        id=base_message.id,
        content=content_blocks,
        model=base_message.model,
        role=base_message.role,
        stop_reason=stop_reason,
        stop_sequence=stop_sequence,
        type=base_message.type,
        usage=usage,
    )

    return message


def _make_content_block(
    chunks: list[anthropic.types.RawMessageStreamEvent], index: int, strict: bool
) -> anthropic.types.ContentBlock:
    """指定されたindexのcontent blockを作成する。"""
    # content_block_startイベントからベースとなるcontent blockを取得
    content_block_start_events = [
        c
        for c in chunks
        if hasattr(c, "type")
        and c.type == "content_block_start"
        and hasattr(c, "index")
        and c.index == index
        and hasattr(c, "content_block")
    ]

    if len(content_block_start_events) == 0:
        raise ValueError(f"content_block_start event not found for index {index}")
    if len(content_block_start_events) > 1:
        _warn(strict, f"複数のcontent_block_startイベントが見つかりました (index={index}): {len(content_block_start_events)}")

    base_content_block = content_block_start_events[0].content_block

    # content_block_deltaイベントからテキストやJSONを収集
    content_block_delta_events = [
        c
        for c in chunks
        if hasattr(c, "type")
        and c.type == "content_block_delta"
        and hasattr(c, "index")
        and c.index == index
        and hasattr(c, "delta")
    ]

    # TextBlockの場合
    if hasattr(base_content_block, "type") and base_content_block.type == "text":
        text_deltas = [
            e.delta.text
            for e in content_block_delta_events
            if isinstance(e.delta, anthropic.types.TextDelta) and hasattr(e.delta, "text")
        ]
        full_text = "".join(text_deltas) if len(text_deltas) > 0 else ""

        # CitationsDeltaの収集
        citations_deltas = [
            e.delta.citation for e in content_block_delta_events if isinstance(e.delta, anthropic.types.CitationsDelta)
        ]
        citations = citations_deltas if len(citations_deltas) > 0 else None

        return anthropic.types.TextBlock.model_construct(type="text", text=full_text, citations=citations)

    # ToolUseBlockの場合
    elif hasattr(base_content_block, "type") and base_content_block.type == "tool_use":
        input_json_deltas = [
            e.delta.partial_json
            for e in content_block_delta_events
            if isinstance(e.delta, anthropic.types.InputJSONDelta) and hasattr(e.delta, "partial_json")
        ]
        full_input_str = "".join(input_json_deltas) if len(input_json_deltas) > 0 else "{}"
        full_input = json.loads(full_input_str)

        return anthropic.types.ToolUseBlock.model_construct(
            type="tool_use", id=base_content_block.id, name=base_content_block.name, input=full_input
        )

    # ThinkingBlockの場合
    elif hasattr(base_content_block, "type") and base_content_block.type == "thinking":
        thinking_deltas = [
            e.delta.thinking
            for e in content_block_delta_events
            if isinstance(e.delta, anthropic.types.ThinkingDelta) and hasattr(e.delta, "thinking")
        ]
        full_thinking = "".join(thinking_deltas) if len(thinking_deltas) > 0 else ""

        # SignatureDeltaの収集
        signature_deltas = [
            e.delta.signature for e in content_block_delta_events if isinstance(e.delta, anthropic.types.SignatureDelta)
        ]
        full_signature = "".join(signature_deltas) if len(signature_deltas) > 0 else ""

        return anthropic.types.ThinkingBlock.model_construct(type="thinking", thinking=full_thinking, signature=full_signature)

    # その他のブロックタイプはそのまま返す
    else:
        return base_content_block


def _aggregate_usage(chunks: list[anthropic.types.RawMessageStreamEvent], strict: bool) -> anthropic.types.Usage:
    """usageを集計する。"""
    del strict  # noqa
    # message_startイベントからベースのusageを取得
    message_start_events = [c for c in chunks if hasattr(c, "type") and c.type == "message_start" and hasattr(c, "message")]
    if len(message_start_events) == 0:
        raise ValueError("message_start event not found")

    base_usage = message_start_events[0].message.usage

    # message_deltaイベントからoutput_tokensの増分を収集
    message_delta_events = [c for c in chunks if hasattr(c, "type") and c.type == "message_delta" and hasattr(c, "usage")]

    output_tokens = base_usage.output_tokens
    for event in message_delta_events:
        output_tokens += event.usage.output_tokens

    # その他のトークン数も集計（message_deltaに含まれる場合）
    cache_creation_input_tokens = base_usage.cache_creation_input_tokens
    cache_read_input_tokens = base_usage.cache_read_input_tokens
    input_tokens = base_usage.input_tokens

    for event in message_delta_events:
        if event.usage.cache_creation_input_tokens is not None:
            cache_creation_input_tokens = (cache_creation_input_tokens or 0) + event.usage.cache_creation_input_tokens
        if event.usage.cache_read_input_tokens is not None:
            cache_read_input_tokens = (cache_read_input_tokens or 0) + event.usage.cache_read_input_tokens
        if event.usage.input_tokens is not None:
            input_tokens += event.usage.input_tokens

    return anthropic.types.Usage.model_construct(
        cache_creation=base_usage.cache_creation,
        cache_creation_input_tokens=cache_creation_input_tokens,
        cache_read_input_tokens=cache_read_input_tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        server_tool_use=base_usage.server_tool_use,
        service_tier=base_usage.service_tier,
    )


@typing.overload
def _equals_all_get[T](strict: bool, name: str, values: typing.Iterable[T], default_value: None = None) -> T | None:
    pass


@typing.overload
def _equals_all_get[T](strict: bool, name: str, values: typing.Iterable[T], default_value: T) -> T:
    pass


def _equals_all_get[T](strict: bool, name: str, values: typing.Iterable[T], default_value: T | None = None) -> T | None:
    """すべての要素が等しいかどうかを確認しつつ最後の要素を返す。"""
    values = list(values)
    # 空文字列や空の値を除外
    non_empty_values = [v for v in values if v != "" and v is not None]
    unique_values = set(non_empty_values)
    if len(unique_values) == 0:
        return default_value
    if len(unique_values) > 1:
        _warn(strict, f"{name}に複数の値が含まれています。{unique_values=}")
    return non_empty_values[-1]


def _warn(strict: bool, message: str) -> None:
    """警告を出力する。"""
    if strict:
        raise ValueError(message)
    logger.warning(message)
