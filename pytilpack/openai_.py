"""OpenAI Python Library用のユーティリティ集。"""

import logging
import typing

import openai
import openai.types.chat

from pytilpack.python_ import coalesce, remove_none

logger = logging.getLogger(__name__)


def gather_chunks(
    chunks: typing.Iterable[openai.types.chat.ChatCompletionChunk],
) -> openai.types.chat.ChatCompletion:
    """ストリーミングのチャンクを結合する。"""
    chunks = list(chunks)
    if len(chunks) == 0:
        return openai.types.chat.ChatCompletion(
            id="", choices=[], created=0, model="", object="chat.completion"
        )
    max_choices = max(len(chunk.choices) for chunk in chunks)
    choices = [_make_choice(chunks, i) for i in range(max_choices)]
    response = openai.types.chat.ChatCompletion.model_construct(
        id=coalesce((c.id for c in chunks), ""),
        choices=choices,
        created=coalesce((c.created for c in chunks), 0),
        model=coalesce((c.model for c in chunks), ""),
        object="chat.completion",
    )
    if (
        system_fingerprint := coalesce(c.system_fingerprint for c in chunks)
    ) is not None:
        response.system_fingerprint = system_fingerprint
    return response


def _make_choice(
    chunks: list[openai.types.chat.ChatCompletionChunk], i: int
) -> openai.types.chat.chat_completion.Choice:
    """ストリーミングのチャンクからChoiceを作成する。"""
    message = openai.types.chat.ChatCompletionMessage.model_construct(role="assistant")
    if (
        len(
            content := remove_none(
                c.choices[i].delta.content for c in chunks if len(c.choices) >= i
            )
        )
        > 0
    ):
        message.content = "".join(content)
    if (
        len(
            function_calls := remove_none(
                c.choices[i].delta.function_call for c in chunks if len(c.choices) >= i
            )
        )
        > 0
    ):
        message.function_call = _make_function_call(function_calls)
    if (
        len(
            tool_calls_list := remove_none(
                c.choices[i].delta.tool_calls for c in chunks if len(c.choices) >= i
            )
        )
        > 0
    ):
        message.tool_calls = _make_tool_calls(tool_calls_list)

    choice = openai.types.chat.chat_completion.Choice.model_construct(
        finish_reason=coalesce(
            (c.choices[i].finish_reason for c in chunks if len(c.choices) >= i), "stop"
        ),
        index=i,
        message=message,
    )
    if (
        logprobs := coalesce(
            c.choices[i].logprobs for c in chunks if len(c.choices) >= i
        )
    ) is not None:
        choice.logprobs = (
            openai.types.chat.chat_completion.ChoiceLogprobs.model_construct(
                content=logprobs.content
            )
        )
    return choice


def _make_function_call(
    deltas: list[openai.types.chat.chat_completion_chunk.ChoiceDeltaFunctionCall],
) -> openai.types.chat.chat_completion_message.FunctionCall | None:
    """ChoiceDeltaFunctionCallを作成する。"""
    if len(deltas) == 0:
        return None
    return openai.types.chat.chat_completion_message.FunctionCall.model_construct(
        arguments="".join(d.arguments for d in deltas if d.arguments is not None),
        name="".join(d.name for d in deltas if d.name is not None),
    )


def _make_tool_calls(
    deltas_list: list[
        list[openai.types.chat.chat_completion_chunk.ChoiceDeltaToolCall]
    ],
) -> (
    list[openai.types.chat.chat_completion_message.ChatCompletionMessageToolCall] | None
):
    """list[ChoiceDeltaToolCall]を作成する。"""
    if len(deltas_list) == 0:
        return None
    max_tool_calls = max(len(deltas) for deltas in deltas_list)
    if max_tool_calls == 0:
        return None
    return [_make_tool_call(deltas_list, i) for i in range(max_tool_calls)]


def _make_tool_call(
    deltas_list: list[
        list[openai.types.chat.chat_completion_chunk.ChoiceDeltaToolCall]
    ],
    i: int,
) -> openai.types.chat.chat_completion_message.ChatCompletionMessageToolCall:
    """ChoiceDeltaToolCallを作成する。"""
    deltas_list = [deltas for deltas in deltas_list if len(deltas) >= i]
    functions = remove_none(deltas[i].function for deltas in deltas_list)
    return openai.types.chat.chat_completion_message.ChatCompletionMessageToolCall.model_construct(
        id=coalesce((deltas[i].id for deltas in deltas_list), ""),
        function=openai.types.chat.chat_completion_message_tool_call.Function.model_construct(
            arguments="".join(remove_none(f.arguments for f in functions)),
            name="".join(remove_none(f.name for f in functions)),
        ),
        type=coalesce((deltas[i].type for deltas in deltas_list), "function"),
    )
