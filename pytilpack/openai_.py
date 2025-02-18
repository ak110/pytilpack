"""OpenAI Python Library用のユーティリティ集。"""

import logging
import typing

import openai
import openai.types.chat

from pytilpack.python_ import coalesce, remove_none

T = typing.TypeVar("T")

logger = logging.getLogger(__name__)


def gather_chunks(
    chunks: typing.Iterable[openai.types.chat.ChatCompletionChunk], strict: bool = False
) -> openai.types.chat.ChatCompletion:
    """ストリーミングのチャンクを結合する。"""
    chunks = list(chunks)
    if len(chunks) == 0:
        return openai.types.chat.ChatCompletion(
            id="", choices=[], created=0, model="", object="chat.completion"
        )

    # max_choices = max(len(chunk.choices) for chunk in chunks)
    min_choice = min(
        (min(c.index for c in chunk.choices) if len(chunk.choices) > 0 else 0)
        for chunk in chunks
    )
    max_choice = max(
        (max(c.index for c in chunk.choices) if len(chunk.choices) > 0 else 0)
        for chunk in chunks
    )
    choices = [
        _make_choice(chunks, i, strict) for i in range(min_choice, max_choice + 1)
    ]

    response = openai.types.chat.ChatCompletion.model_construct(
        id=_equals_all_get(strict, "id", remove_none(c.id for c in chunks), ""),
        choices=choices,
        created=coalesce((c.created for c in chunks), 0),
        model=_equals_all_get(
            strict, "model", remove_none(c.model for c in chunks), ""
        ),
        object="chat.completion",
        service_tier=_equals_all_get(
            strict, "service_tier", remove_none(c.service_tier for c in chunks)
        ),
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
        (
            [
                choice
                for choice in chunk.choices
                if choice is not None and choice.index == index
            ]
            for chunk in chunks
        ),
        [],
    )

    message = openai.types.chat.ChatCompletionMessage.model_construct()

    if len(roles := remove_none(c.delta.role for c in choice_list)) > 0:
        message.role = _equals_all_get(strict, "role", roles, "assistant")  # type: ignore

    if len(contents := remove_none(c.delta.content for c in choice_list)) > 0:
        message.content = "".join(contents)

    if (
        len(function_calls := remove_none(c.delta.function_call for c in choice_list))
        > 0
    ):
        message.function_call = _make_function_call(function_calls, strict)

    if len(tool_calls_list := remove_none(c.delta.tool_calls for c in choice_list)) > 0:
        message.tool_calls = _make_tool_calls(tool_calls_list, strict)

    choice = openai.types.chat.chat_completion.Choice.model_construct(
        index=index, message=message
    )

    if len(finish_reasons := remove_none(c.finish_reason for c in choice_list)) > 0:
        choice.finish_reason = _equals_all_get(strict, "finish_reason", finish_reasons)  # type: ignore

    if len(logprobs_list := remove_none(c.logprobs for c in choice_list)) > 0:
        if len(logprobs_list) > 1:
            _warn(
                strict,
                f"logprobsが複数存在します。最後のlogprobsを使用します。{logprobs_list=}",
            )
        choice.logprobs = (
            openai.types.chat.chat_completion.ChoiceLogprobs.model_construct(
                content=logprobs_list[-1].content
            )
        )

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
        name=_equals_all_get(
            strict, "function.name", remove_none(d.name for d in deltas)
        ),
    )


def _make_tool_calls(
    tool_calls_list: list[
        list[openai.types.chat.chat_completion_chunk.ChoiceDeltaToolCall]
    ],
    strict: bool,
) -> (
    list[openai.types.chat.chat_completion_message.ChatCompletionMessageToolCall] | None
):
    """list[ChoiceDeltaToolCall]を作成する。"""
    if len(tool_calls_list) == 0:
        return None
    min_tool_call = min(
        (min(d.index for d in deltas) if len(deltas) > 0 else 0)
        for deltas in tool_calls_list
    )
    max_tool_call = max(
        (max(d.index for d in deltas) if len(deltas) > 0 else 0)
        for deltas in tool_calls_list
    )
    return [
        _make_tool_call(tool_calls_list, i, strict)
        for i in range(min_tool_call, max_tool_call + 1)
    ]


def _make_tool_call(
    tool_calls_list: list[
        list[openai.types.chat.chat_completion_chunk.ChoiceDeltaToolCall]
    ],
    index: int,
    strict: bool,
) -> openai.types.chat.chat_completion_message.ChatCompletionMessageToolCall:
    """ChoiceDeltaToolCallを作成する。"""
    tool_call_list = sum(
        (
            [
                tool_call
                for tool_call in tool_calls
                if tool_call is not None and tool_call.index == index
            ]
            for tool_calls in tool_calls_list
        ),
        [],
    )

    tool_call = (
        openai.types.chat.chat_completion_message.ChatCompletionMessageToolCall.model_construct()
    )

    if len(ids := remove_none(delta.id for delta in tool_call_list)) > 0:
        tool_call.id = _equals_all_get(strict, f"delta.tool_calls[{index}].id", ids, "")

    if len(types := remove_none(delta.type for delta in tool_call_list)) > 0:
        tool_call.type = _equals_all_get(strict, f"delta.tool_calls[{index}].type", types)  # type: ignore[assignment]

    if len(functions := remove_none(delta.function for delta in tool_call_list)) > 0:
        tool_call.function = (
            openai.types.chat.chat_completion_message_tool_call.Function(
                arguments="".join(remove_none(f.arguments for f in functions)),
                name=_equals_all_get(
                    strict,
                    f"delta.tool_calls[{index}].function.name",
                    remove_none(f.name for f in functions),
                    "",
                ),
            )
        )

    return tool_call


@typing.overload
def _equals_all_get(
    strict: bool, name: str, values: typing.Iterable[T], default_value: None = None
) -> T | None:
    pass


@typing.overload
def _equals_all_get(
    strict: bool, name: str, values: typing.Iterable[T], default_value: T
) -> T:
    pass


def _equals_all_get(
    strict: bool, name: str, values: typing.Iterable[T], default_value: T | None = None
) -> T | None:
    """すべての要素が等しいかどうかを確認しつつ最後の要素を返す。"""
    values = list(values)
    unique_values = set(values)
    if len(unique_values) == 0:
        return default_value
    if len(unique_values) > 1:
        _warn(strict, f"{name}に複数の値が含まれています。{unique_values=}")
    return values[-1]


def _get_single(strict: bool, name: str, values: typing.Iterable[T]) -> T | None:
    """リストの要素が1つだけであることを確認して取得する。"""
    values = list(values)
    if len(values) == 0:
        return None
    if len(values) > 1:
        _warn(strict, f"{name}に複数の値が含まれています。{values=}")
    return values[0]


def _warn(strict: bool, message: str) -> None:
    """警告を出力する。"""
    if strict:
        raise ValueError(message)
    logger.warning(message)
