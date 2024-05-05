"""テストコード。"""

import openai
import openai.types.chat

import pytilpack.openai_


def test_gather_chunks():
    """gather_chunksのテスト。"""
    chunks = [
        openai.types.chat.ChatCompletionChunk(
            id="id",
            choices=[
                openai.types.chat.chat_completion_chunk.Choice(
                    index=0,
                    delta=openai.types.chat.chat_completion_chunk.ChoiceDelta(
                        role="assistant"
                    ),
                )
            ],
            created=0,
            model="gpt-3.5-turbo",
            object="chat.completion.chunk",
        ),
        openai.types.chat.ChatCompletionChunk(
            id="id",
            choices=[
                openai.types.chat.chat_completion_chunk.Choice(
                    index=0,
                    delta=openai.types.chat.chat_completion_chunk.ChoiceDelta(
                        content="cont"
                    ),
                )
            ],
            created=0,
            model="gpt-3.5-turbo",
            object="chat.completion.chunk",
            system_fingerprint="fingerprint",
        ),
        openai.types.chat.ChatCompletionChunk(
            id="id",
            choices=[
                openai.types.chat.chat_completion_chunk.Choice(
                    index=0,
                    delta=openai.types.chat.chat_completion_chunk.ChoiceDelta(
                        content="ent"
                    ),
                    finish_reason="stop",
                )
            ],
            created=0,
            model="gpt-3.5-turbo",
            object="chat.completion.chunk",
        ),
    ]
    actual = pytilpack.openai_.gather_chunks(chunks)
    expected = openai.types.chat.ChatCompletion(
        id="id",
        choices=[
            openai.types.chat.chat_completion.Choice(
                finish_reason="stop",
                index=0,
                message=openai.types.chat.ChatCompletionMessage(
                    content="content", role="assistant"
                ),
            )
        ],
        created=0,
        model="gpt-3.5-turbo",
        object="chat.completion",
        system_fingerprint="fingerprint",
        usage=None,
    )
    assert actual.model_dump() == expected.model_dump()
