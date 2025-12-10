"""OpenAI Python Library用のユーティリティ集。"""

import logging
import typing

import openai
import openai.types.chat
import openai.types.chat.chat_completion
import openai.types.chat.chat_completion_chunk
import openai.types.chat.chat_completion_message
import openai.types.chat.chat_completion_message_function_tool_call
import openai.types.chat.chat_completion_message_tool_call
import openai.types.responses
import openai.types.responses.response
import openai.types.responses.response_output_item

from pytilpack.python import coalesce, remove_none

logger = logging.getLogger(__name__)


def gather_chunks(
    chunks: typing.Iterable[openai.types.chat.ChatCompletionChunk], strict: bool = False
) -> openai.types.chat.ChatCompletion:
    """ストリーミングのチャンクを結合する。"""
    chunks = list(chunks)
    if len(chunks) == 0:
        return openai.types.chat.ChatCompletion(id="", choices=[], created=0, model="", object="chat.completion")

    # chunks[i].choices は型ヒント上はList[Choice]だが、Noneが入っている場合がある
    min_choice = min(
        (min(c.index for c in chunk.choices) if chunk.choices is not None and len(chunk.choices) > 0 else 0) for chunk in chunks
    )
    max_choice = max(
        (max(c.index for c in chunk.choices) if chunk.choices is not None and len(chunk.choices) > 0 else 0) for chunk in chunks
    )
    choices = [_make_choice(chunks, i, strict) for i in range(min_choice, max_choice + 1)]

    response = openai.types.chat.ChatCompletion.model_construct(
        id=_equals_all_get(strict, "id", remove_none(c.id for c in chunks), ""),
        choices=choices,
        created=coalesce((c.created for c in chunks), 0),
        model=_equals_all_get(strict, "model", remove_none(c.model for c in chunks), ""),
        object="chat.completion",
        service_tier=_equals_all_get(strict, "service_tier", remove_none(c.service_tier for c in chunks)),
        system_fingerprint=_equals_all_get(
            strict,
            "system_fingerprint",
            remove_none(c.system_fingerprint for c in chunks),
        ),
        usage=_get_single(strict, "usage", remove_none(c.usage for c in chunks)),
    )
    return response


def _make_choice(
    chunks: list[openai.types.chat.ChatCompletionChunk], index: int, strict: bool
) -> openai.types.chat.chat_completion.Choice:
    """ストリーミングのチャンクからi番目のChoiceを作成する。"""
    choice_list = sum(
        ([choice for choice in chunk.choices if choice is not None and choice.index == index] for chunk in chunks),
        [],
    )

    message = openai.types.chat.ChatCompletionMessage.model_construct()

    if len(roles := remove_none(c.delta.role for c in choice_list)) > 0:
        message.role = _equals_all_get(strict, "role", roles, "assistant")  # type: ignore

    if len(contents := remove_none(c.delta.content for c in choice_list)) > 0:
        message.content = "".join(contents)

    if len(refusals := remove_none(c.delta.refusal for c in choice_list)) > 0:
        message.refusal = "".join(refusals)

    if len(function_calls := remove_none(c.delta.function_call for c in choice_list)) > 0:
        message.function_call = _make_function_call(function_calls, strict)

    if len(tool_calls_list := remove_none(c.delta.tool_calls for c in choice_list)) > 0:
        message.tool_calls = _make_tool_calls(tool_calls_list, strict)

    choice = openai.types.chat.chat_completion.Choice.model_construct(index=index, message=message)

    if len(finish_reasons := remove_none(c.finish_reason for c in choice_list)) > 0:
        choice.finish_reason = _equals_all_get(strict, "finish_reason", finish_reasons)  # type: ignore

    if len(logprobs_list := remove_none(c.logprobs for c in choice_list)) > 0:
        if len(logprobs_list) > 1:
            _warn(
                strict,
                f"logprobsが複数存在します。最後のlogprobsを使用します。{logprobs_list=}",
            )
        choice.logprobs = openai.types.chat.chat_completion.ChoiceLogprobs.model_construct(content=logprobs_list[-1].content)

    return choice


def _make_function_call(
    deltas: list[openai.types.chat.chat_completion_chunk.ChoiceDeltaFunctionCall],
    strict: bool,
) -> openai.types.chat.chat_completion_message.FunctionCall | None:
    """ChoiceDeltaFunctionCallを作成する。"""
    if len(deltas) == 0:
        return None
    return openai.types.chat.chat_completion_message.FunctionCall.model_construct(
        arguments="".join(remove_none(d.arguments for d in deltas)),
        name=_equals_all_get(strict, "function.name", remove_none(d.name for d in deltas)),
    )


def _make_tool_calls(
    tool_calls_list: list[list[openai.types.chat.chat_completion_chunk.ChoiceDeltaToolCall]],
    strict: bool,
) -> list[openai.types.chat.chat_completion_message_tool_call.ChatCompletionMessageToolCallUnion] | None:
    """list[ChoiceDeltaToolCall]を作成する。"""
    if len(tool_calls_list) == 0:
        return None
    min_tool_call = min((min(d.index for d in deltas) if len(deltas) > 0 else 0) for deltas in tool_calls_list)
    max_tool_call = max((max(d.index for d in deltas) if len(deltas) > 0 else 0) for deltas in tool_calls_list)
    return [_make_tool_call(tool_calls_list, i, strict) for i in range(min_tool_call, max_tool_call + 1)]


def _make_tool_call(
    tool_calls_list: list[list[openai.types.chat.chat_completion_chunk.ChoiceDeltaToolCall]],
    index: int,
    strict: bool,
) -> openai.types.chat.chat_completion_message_tool_call.ChatCompletionMessageToolCallUnion:
    """ChoiceDeltaToolCallを作成する。"""
    tool_call_list = sum(
        (
            [tool_call for tool_call in tool_calls if tool_call is not None and tool_call.index == index]
            for tool_calls in tool_calls_list
        ),
        [],
    )

    tool_call = (
        openai.types.chat.chat_completion_message_function_tool_call.ChatCompletionMessageFunctionToolCall.model_construct()
    )

    if len(ids := remove_none(delta.id for delta in tool_call_list)) > 0:
        tool_call.id = _equals_all_get(strict, f"delta.tool_calls[{index}].id", ids, "")

    if len(types := remove_none(delta.type for delta in tool_call_list)) > 0:
        tool_call.type = _equals_all_get(strict, f"delta.tool_calls[{index}].type", types)  # type: ignore[assignment]

    if len(functions := remove_none(delta.function for delta in tool_call_list)) > 0:
        tool_call.function = openai.types.chat.chat_completion_message_function_tool_call.Function(
            arguments="".join(remove_none(f.arguments for f in functions)),
            name=_equals_all_get(
                strict,
                f"delta.tool_calls[{index}].function.name",
                remove_none(f.name for f in functions),
                "",
            ),
        )

    return tool_call


def gather_events(
    events: typing.Iterable[openai.types.responses.ResponseStreamEvent], strict: bool = False
) -> openai.types.responses.Response:
    """gather_chunks の Responses API版。"""
    events = list(events)
    if len(events) == 0:
        return openai.types.responses.Response(
            id="",
            created_at=0,
            model="",  # type: ignore
            object="response",
            output=[],
            parallel_tool_calls=False,
            tool_choice="auto",
            tools=[],
        )

    response = _accumulate_events(events, strict)
    return response


def _accumulate_events(
    events: list[openai.types.responses.ResponseStreamEvent], strict: bool
) -> openai.types.responses.Response:
    """イベントを蓄積してResponseを構築する。"""
    snapshot: openai.types.responses.Response | None = None
    completed_response: openai.types.responses.Response | None = None

    for event in events:
        if event.type == "response.created":
            snapshot = _create_initial_response(event)
        elif event.type == "response.completed":
            completed_response = event.response
        elif snapshot is not None:
            _accumulate_event_to_snapshot(snapshot, event, strict)

    if completed_response is not None:
        return completed_response

    if snapshot is None:
        _warn(strict, "response.createdイベントが見つかりませんでした")
        return openai.types.responses.Response(
            id="",
            created_at=0,
            model="",  # type: ignore
            object="response",
            output=[],
            parallel_tool_calls=False,
            tool_choice="auto",
            tools=[],
        )

    return snapshot


def _create_initial_response(
    event: openai.types.responses.ResponseStreamEvent,
) -> openai.types.responses.Response:
    """response.createdイベントから初期Responseを作成する。"""
    if not hasattr(event, "response"):
        raise ValueError("response.createdイベントにresponseが含まれていません")
    return typing.cast(openai.types.responses.Response, event.response)  # type: ignore[attr-defined]


def _accumulate_event_to_snapshot(
    snapshot: openai.types.responses.Response,
    event: openai.types.responses.ResponseStreamEvent,
    strict: bool,
) -> None:
    """イベントをスナップショットに蓄積する。"""
    if event.type == "response.output_item.added":
        _accumulate_output_item_added(snapshot, event)
    elif event.type == "response.content_part.added":
        _accumulate_content_part_added(snapshot, event)
    elif event.type == "response.output_text.delta":
        _accumulate_output_text_delta(snapshot, event, strict)
    elif event.type == "response.refusal.delta":
        _accumulate_output_refusal_delta(snapshot, event, strict)
    elif event.type == "response.function_call_arguments.delta":
        _accumulate_function_call_arguments_delta(snapshot, event, strict)
    elif event.type == "response.audio.transcript.delta":
        _accumulate_audio_transcript_delta(snapshot, event, strict)
    elif event.type == "response.reasoning_text.delta":
        _accumulate_reasoning_text_delta(snapshot, event, strict)
    elif event.type == "response.reasoning_summary_text.delta":
        _accumulate_reasoning_summary_text_delta(snapshot, event, strict)
    elif event.type == "response.custom_tool_call_input.delta":
        _accumulate_custom_tool_call_input_delta(snapshot, event, strict)
    elif event.type == "response.mcp_call_arguments.delta":
        _accumulate_mcp_call_arguments_delta(snapshot, event, strict)
    elif event.type == "response.code_interpreter_call_code.delta":
        _accumulate_code_interpreter_call_code_delta(snapshot, event, strict)


def _accumulate_output_item_added(
    snapshot: openai.types.responses.Response,
    event: openai.types.responses.ResponseStreamEvent,
) -> None:
    """output_item.addedイベントを蓄積する。"""
    if not hasattr(event, "item"):
        return
    snapshot.output.append(event.item)  # type: ignore[attr-defined]


def _accumulate_content_part_added(
    snapshot: openai.types.responses.Response,
    event: openai.types.responses.ResponseStreamEvent,
) -> None:
    """content_part.addedイベントを蓄積する。"""
    if not hasattr(event, "output_index") or not hasattr(event, "part"):
        return
    output_index = event.output_index  # type: ignore[attr-defined]
    if output_index >= len(snapshot.output):
        return
    output = snapshot.output[output_index]
    if output.type == "message":
        output.content.append(event.part)  # type: ignore[attr-defined,arg-type]


def _accumulate_output_text_delta(
    snapshot: openai.types.responses.Response,
    event: openai.types.responses.ResponseStreamEvent,
    strict: bool,
) -> None:
    """output_text.deltaイベントを蓄積する。"""
    if not hasattr(event, "output_index") or not hasattr(event, "content_index") or not hasattr(event, "delta"):
        return
    output_index = event.output_index  # type: ignore[attr-defined]
    content_index = event.content_index  # type: ignore[attr-defined]
    if output_index >= len(snapshot.output):
        _warn(strict, f"output_index {output_index} が範囲外です")
        return
    output = snapshot.output[output_index]
    if output.type == "message":
        if content_index >= len(output.content):
            _warn(strict, f"content_index {content_index} が範囲外です")
            return
        content = output.content[content_index]
        if content.type == "output_text":
            content.text += event.delta  # type: ignore[attr-defined]


def _accumulate_output_refusal_delta(
    snapshot: openai.types.responses.Response,
    event: openai.types.responses.ResponseStreamEvent,
    strict: bool,
) -> None:
    """output_refusal.deltaイベントを蓄積する。"""
    if not hasattr(event, "output_index") or not hasattr(event, "content_index") or not hasattr(event, "delta"):
        return
    output_index = event.output_index  # type: ignore[attr-defined]
    content_index = event.content_index  # type: ignore[attr-defined]
    if output_index >= len(snapshot.output):
        _warn(strict, f"output_index {output_index} が範囲外です")
        return
    output = snapshot.output[output_index]
    if output.type == "message":
        if content_index >= len(output.content):
            _warn(strict, f"content_index {content_index} が範囲外です")
            return
        content = output.content[content_index]
        if content.type == "refusal":  # type: ignore[comparison-overlap]
            content.refusal += event.delta  # type: ignore[attr-defined]


def _accumulate_function_call_arguments_delta(
    snapshot: openai.types.responses.Response,
    event: openai.types.responses.ResponseStreamEvent,
    strict: bool,
) -> None:
    """function_call_arguments.deltaイベントを蓄積する。"""
    if not hasattr(event, "output_index") or not hasattr(event, "delta"):
        return
    output_index = event.output_index  # type: ignore[attr-defined]
    if output_index >= len(snapshot.output):
        _warn(strict, f"output_index {output_index} が範囲外です")
        return
    output = snapshot.output[output_index]
    if output.type == "function_call":
        output.arguments += event.delta  # type: ignore[attr-defined]


def _accumulate_audio_transcript_delta(
    snapshot: openai.types.responses.Response,
    event: openai.types.responses.ResponseStreamEvent,
    strict: bool,
) -> None:
    """audio_transcript.deltaイベントを蓄積する。"""
    if not hasattr(event, "output_index") or not hasattr(event, "content_index") or not hasattr(event, "delta"):
        return
    output_index = event.output_index  # type: ignore[attr-defined]
    content_index = event.content_index  # type: ignore[attr-defined]
    if output_index >= len(snapshot.output):
        _warn(strict, f"output_index {output_index} が範囲外です")
        return
    output = snapshot.output[output_index]
    if output.type == "message":
        if content_index >= len(output.content):
            _warn(strict, f"content_index {content_index} が範囲外です")
            return
        content = output.content[content_index]
        if content.type == "output_audio" and hasattr(content, "transcript"):  # type: ignore[comparison-overlap]
            content.transcript += event.delta  # type: ignore[attr-defined]


def _accumulate_reasoning_text_delta(
    snapshot: openai.types.responses.Response,
    event: openai.types.responses.ResponseStreamEvent,
    strict: bool,
) -> None:
    """reasoning_text.deltaイベントを蓄積する。"""
    if not hasattr(event, "output_index") or not hasattr(event, "content_index") or not hasattr(event, "delta"):
        return
    output_index = event.output_index  # type: ignore[attr-defined]
    content_index = event.content_index  # type: ignore[attr-defined]
    if output_index >= len(snapshot.output):
        _warn(strict, f"output_index {output_index} が範囲外です")
        return
    output = snapshot.output[output_index]
    if output.type == "message":
        if content_index >= len(output.content):
            _warn(strict, f"content_index {content_index} が範囲外です")
            return
        content = output.content[content_index]
        if content.type == "reasoning_text":  # type: ignore[comparison-overlap]
            content.text += event.delta  # type: ignore[attr-defined]


def _accumulate_reasoning_summary_text_delta(
    snapshot: openai.types.responses.Response,
    event: openai.types.responses.ResponseStreamEvent,
    strict: bool,
) -> None:
    """reasoning_summary_text.deltaイベントを蓄積する。"""
    if not hasattr(event, "output_index") or not hasattr(event, "content_index") or not hasattr(event, "delta"):
        return
    output_index = event.output_index  # type: ignore[attr-defined]
    content_index = event.content_index  # type: ignore[attr-defined]
    if output_index >= len(snapshot.output):
        _warn(strict, f"output_index {output_index} が範囲外です")
        return
    output = snapshot.output[output_index]
    if output.type == "message":
        if content_index >= len(output.content):
            _warn(strict, f"content_index {content_index} が範囲外です")
            return
        content = output.content[content_index]
        if content.type == "reasoning_summary" and hasattr(content, "text"):  # type: ignore[comparison-overlap]
            content.text += event.delta  # type: ignore[attr-defined]


def _accumulate_custom_tool_call_input_delta(
    snapshot: openai.types.responses.Response,
    event: openai.types.responses.ResponseStreamEvent,
    strict: bool,
) -> None:
    """custom_tool_call_input.deltaイベントを蓄積する。"""
    if not hasattr(event, "output_index") or not hasattr(event, "delta"):
        return
    output_index = event.output_index  # type: ignore[attr-defined]
    if output_index >= len(snapshot.output):
        _warn(strict, f"output_index {output_index} が範囲外です")
        return
    output = snapshot.output[output_index]
    if output.type == "custom_tool_call":
        output.input += event.delta  # type: ignore[attr-defined]


def _accumulate_mcp_call_arguments_delta(
    snapshot: openai.types.responses.Response,
    event: openai.types.responses.ResponseStreamEvent,
    strict: bool,
) -> None:
    """mcp_call_arguments.deltaイベントを蓄積する。"""
    if not hasattr(event, "output_index") or not hasattr(event, "delta"):
        return
    output_index = event.output_index  # type: ignore[attr-defined]
    if output_index >= len(snapshot.output):
        _warn(strict, f"output_index {output_index} が範囲外です")
        return
    output = snapshot.output[output_index]
    if output.type == "mcp_call":
        output.arguments += event.delta  # type: ignore[attr-defined]


def _accumulate_code_interpreter_call_code_delta(
    snapshot: openai.types.responses.Response,
    event: openai.types.responses.ResponseStreamEvent,
    strict: bool,
) -> None:
    """code_interpreter_call_code.deltaイベントを蓄積する。"""
    if not hasattr(event, "output_index") or not hasattr(event, "delta"):
        return
    output_index = event.output_index  # type: ignore[attr-defined]
    if output_index >= len(snapshot.output):
        _warn(strict, f"output_index {output_index} が範囲外です")
        return
    output = snapshot.output[output_index]
    if output.type == "code_interpreter_call":
        output.code += event.delta  # type: ignore[attr-defined,operator]


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


def _get_single[T](strict: bool, name: str, values: typing.Iterable[T]) -> T | None:
    """リストの要素が1つだけであることを確認して取得する。"""
    values = list(values)
    # 空文字列や空の値を除外
    non_empty_values = [v for v in values if v != "" and v is not None]
    if len(non_empty_values) == 0:
        return None
    if len(non_empty_values) > 1:
        _warn(strict, f"{name}に複数の値が含まれています。{values=}")
    return non_empty_values[0]


def _warn(strict: bool, message: str) -> None:
    """警告を出力する。"""
    if strict:
        raise ValueError(message)
    logger.warning(message)
