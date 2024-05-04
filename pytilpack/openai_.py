"""OpenAI Python Library用のユーティリティ集。"""

import openai
import openai.types.chat

import pytilpack.python_


def gather_chunks(
    chunks: list[openai.types.chat.ChatCompletionChunk],
) -> openai.types.chat.ChatCompletion:
    """ストリーミングのチャンクを結合する。"""
    max_choices = max(len(chunk.choices) for chunk in chunks)
    choices = [_make_choice(chunks, i) for i in range(max_choices)]
    return openai.types.chat.ChatCompletion(
        id=chunks[0].id,
        choices=choices,
        created=chunks[0].created,
        model=chunks[0].model,
        object="chat.completion",
        system_fingerprint=chunks[0].system_fingerprint,
    )


def _make_choice(
    chunks: list[openai.types.chat.ChatCompletionChunk], i: int
) -> openai.types.chat.chat_completion.Choice:
    """ストリーミングのチャンクからChoiceを作成する。"""
    logprobs = pytilpack.python_.coalesce(
        c.choices[i].logprobs for c in chunks if len(c.choices) >= i
    )
    return openai.types.chat.chat_completion.Choice(
        finish_reason=pytilpack.python_.coalesce(
            (c.choices[i].finish_reason for c in chunks if len(c.choices) >= i), "stop"
        ),
        index=i,
        logprobs=(
            None
            if logprobs is None
            else openai.types.chat.chat_completion.ChoiceLogprobs(
                content=logprobs.content
            )
        ),
        message=openai.types.chat.ChatCompletionMessage(
            content="".join(
                pytilpack.python_.remove_none(
                    c.choices[i].delta.content for c in chunks if len(c.choices) >= i
                )
            ),
            # role=pytilpack.python_.coalesce(
            #     (c.choices[i].delta.role for c in chunks if len(c.choices) >= i),
            #     "assistant",
            # ),
            role="assistant",
            function_call=_make_function_call(
                pytilpack.python_.remove_none(
                    c.choices[i].delta.function_call
                    for c in chunks
                    if len(c.choices) >= i
                )
            ),
            tool_calls=_make_tool_calls(
                pytilpack.python_.remove_none(
                    c.choices[i].delta.tool_calls for c in chunks if len(c.choices) >= i
                )
            ),
        ),
    )


def _make_function_call(
    deltas: list[openai.types.chat.chat_completion_chunk.ChoiceDeltaFunctionCall],
) -> openai.types.chat.chat_completion_message.FunctionCall | None:
    """ChoiceDeltaFunctionCallを作成する。"""
    if len(deltas) == 0:
        return None
    return openai.types.chat.chat_completion_message.FunctionCall(
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
    functions = pytilpack.python_.remove_none(
        deltas[i].function for deltas in deltas_list
    )
    return openai.types.chat.chat_completion_message.ChatCompletionMessageToolCall(
        id=pytilpack.python_.coalesce((deltas[i].id for deltas in deltas_list), ""),
        function=openai.types.chat.chat_completion_message_tool_call.Function(
            arguments="".join(
                pytilpack.python_.remove_none(f.arguments for f in functions)
            ),
            name="".join(pytilpack.python_.remove_none(f.name for f in functions)),
        ),
        type=pytilpack.python_.coalesce(
            (deltas[i].type for deltas in deltas_list), "function"
        ),
    )
