"""テストコード。"""

import pathlib

import flask
import openai
import openai.types.chat

import pytilpack.flask_
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
    actual = pytilpack.openai_.gather_chunks(chunks, strict=True)
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


def test_gather_chunks_claude_tools():
    """gather_chunksのテスト。Claude+LiteLLM?で出てきた謎パターン風のテスト。"""
    chunks = [
        openai.types.chat.ChatCompletionChunk(
            id="id",
            choices=[
                openai.types.chat.chat_completion_chunk.Choice(
                    index=0,
                    delta=openai.types.chat.chat_completion_chunk.ChoiceDelta(
                        role="assistant",
                        content="aaa",
                        tool_calls=[
                            openai.types.chat.chat_completion_chunk.ChoiceDeltaToolCall(
                                index=1,  # 何故か1から始まる
                                id="id123",
                                function=openai.types.chat.chat_completion_chunk.ChoiceDeltaToolCallFunction(
                                    name="funcname", arguments=None
                                ),
                            ),
                            openai.types.chat.chat_completion_chunk.ChoiceDeltaToolCall(
                                index=1,  # 何故か同じチャンク内で分けて送られてくる
                                function=openai.types.chat.chat_completion_chunk.ChoiceDeltaToolCallFunction(
                                    name=None, arguments='{"expression":"1+1"}'
                                ),
                            ),
                            openai.types.chat.chat_completion_chunk.ChoiceDeltaToolCall(
                                index=1, type="function"
                            ),
                        ],
                    ),
                    finish_reason="tool_calls",
                )
            ],
            created=123,
            model="anthropic.claude-3-5-sonnet-20240620-v1:0",
            object="chat.completion.chunk",
            system_fingerprint="fingerprint",
        )
    ]
    actual = pytilpack.openai_.gather_chunks(chunks, strict=True)
    expected = openai.types.chat.ChatCompletion(
        id="id",
        choices=[
            openai.types.chat.chat_completion.Choice(
                index=0,
                message=openai.types.chat.ChatCompletionMessage(
                    content="aaa",
                    role="assistant",
                    tool_calls=[
                        openai.types.chat.ChatCompletionMessageToolCall(
                            id="id123",
                            function=openai.types.chat.chat_completion_message_tool_call.Function(
                                arguments='{"expression":"1+1"}', name="funcname"
                            ),
                            type="function",
                        )
                    ],
                ),
                finish_reason="tool_calls",
            )
        ],
        created=123,
        model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        object="chat.completion",
        system_fingerprint="fingerprint",
        usage=None,
    )
    assert actual.model_dump() == expected.model_dump()


def test_gather_chunks_stream(data_dir: pathlib.Path):
    app = flask.Flask(__name__)

    @app.route("/v1/chat/completions", methods=["POST"])
    def mock_chat_completions():
        response_body = (
            (data_dir / "openai.chat.stream.txt")
            .read_text(encoding="utf-8")
            .split("\r\n\r\n", 1)[-1]
        )
        return flask.Response(
            response_body.split("\r\n"), content_type="text/event-stream"
        )

    with pytilpack.flask_.run(app):
        response = openai.OpenAI(
            api_key="sk-dummy", base_url="http://localhost:5000/v1"
        ).chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "1+1=?"}],
            stream=True,
        )
        actual = pytilpack.openai_.gather_chunks(response, strict=True)
        expected = openai.types.chat.ChatCompletion(
            id="chatcmpl-9LkPsGgzcOKvsoNpPxy722wmnc8Ij",
            choices=[
                openai.types.chat.chat_completion.Choice(
                    finish_reason="stop",
                    index=0,
                    message=openai.types.chat.ChatCompletionMessage(
                        content="1+1=2", role="assistant"
                    ),
                )
            ],
            created=1714970340,
            model="gpt-3.5-turbo-0125",
            object="chat.completion",
            system_fingerprint="fp_a450710239",
        )
        assert actual.model_dump() == expected.model_dump()


def test_gather_chunks_function1(data_dir: pathlib.Path):
    app = flask.Flask(__name__)

    @app.route("/v1/chat/completions", methods=["POST"])
    def mock_chat_completions():
        response_body = (
            (data_dir / "openai.chat.function1.txt")
            .read_text(encoding="utf-8")
            .split("\r\n\r\n", 1)[-1]
        )
        return flask.Response(
            response_body.split("\r\n"), content_type="text/event-stream"
        )

    with pytilpack.flask_.run(app):
        response = openai.OpenAI(
            api_key="sk-dummy", base_url="http://localhost:5000/v1"
        ).chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "1+1=?"}],
            stream=True,
        )
        actual = pytilpack.openai_.gather_chunks(response, strict=True)
        expected = openai.types.chat.ChatCompletion(
            id="chatcmpl-9Lkf3AWNcFV03tyCd5LaAXb2xgZ65",
            choices=[
                openai.types.chat.chat_completion.Choice(
                    finish_reason="tool_calls",
                    index=0,
                    message=openai.types.chat.ChatCompletionMessage(
                        role="assistant",
                        tool_calls=[
                            openai.types.chat.ChatCompletionMessageToolCall(
                                id="call_flA5AHMfQwJYLsdQFXSk81YA",
                                function=openai.types.chat.chat_completion_message_tool_call.Function(
                                    arguments='{"expression":"1+1"}', name="calculator"
                                ),
                                type="function",
                            )
                        ],
                    ),
                )
            ],
            created=1714971281,
            model="gpt-3.5-turbo-0125",
            object="chat.completion",
            system_fingerprint="fp_3b956da36b",
            usage=None,
        )
        assert actual.model_dump() == expected.model_dump()


def test_gather_chunks_function2(data_dir: pathlib.Path):
    app = flask.Flask(__name__)

    @app.route("/v1/chat/completions", methods=["POST"])
    def mock_chat_completions():
        response_body = (
            (data_dir / "openai.chat.function2.txt")
            .read_text(encoding="utf-8")
            .split("\r\n\r\n", 1)[-1]
        )
        return flask.Response(
            response_body.split("\r\n"), content_type="text/event-stream"
        )

    with pytilpack.flask_.run(app):
        response = openai.OpenAI(
            api_key="sk-dummy", base_url="http://localhost:5000/v1"
        ).chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "1+1=?"}],
            stream=True,
        )
        actual = pytilpack.openai_.gather_chunks(response, strict=True)
        expected = openai.types.chat.ChatCompletion(
            id="chatcmpl-9LkecCMw4qvicGMfOU00PBHbVbpNL",
            choices=[
                openai.types.chat.chat_completion.Choice(
                    finish_reason="stop",
                    index=0,
                    message=openai.types.chat.ChatCompletionMessage(
                        content="The result of 1 + 1 is 789.", role="assistant"
                    ),
                )
            ],
            created=1714971254,
            model="gpt-3.5-turbo-0125",
            object="chat.completion",
            system_fingerprint="fp_3b956da36b",
        )
        assert actual.model_dump() == expected.model_dump()
