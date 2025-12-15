"""テストコード。"""

import pathlib

import flask
import openai
import openai.types.chat
import openai.types.chat.chat_completion
import openai.types.chat.chat_completion_chunk
import openai.types.chat.chat_completion_message_function_tool_call
import openai.types.responses
import openai.types.responses.response
import openai.types.responses.response_output_item

import pytilpack.flask
import pytilpack.openai


def test_gather_chunks():
    """gather_chunksのテスト。"""
    chunks = [
        openai.types.chat.ChatCompletionChunk(
            id="id",
            choices=[
                openai.types.chat.chat_completion_chunk.Choice(
                    index=0,
                    delta=openai.types.chat.chat_completion_chunk.ChoiceDelta(role="assistant"),
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
                    delta=openai.types.chat.chat_completion_chunk.ChoiceDelta(content="cont"),
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
                    delta=openai.types.chat.chat_completion_chunk.ChoiceDelta(content="ent"),
                    finish_reason="stop",
                )
            ],
            created=0,
            model="gpt-3.5-turbo",
            object="chat.completion.chunk",
        ),
    ]
    actual = pytilpack.openai.gather_chunks(chunks, strict=True)
    expected = openai.types.chat.ChatCompletion(
        id="id",
        choices=[
            openai.types.chat.chat_completion.Choice(
                finish_reason="stop",
                index=0,
                message=openai.types.chat.ChatCompletionMessage(content="content", role="assistant"),
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
                            openai.types.chat.chat_completion_chunk.ChoiceDeltaToolCall(index=1, type="function"),
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
    actual = pytilpack.openai.gather_chunks(chunks, strict=True)
    expected = openai.types.chat.ChatCompletion(
        id="id",
        choices=[
            openai.types.chat.chat_completion.Choice(
                index=0,
                message=openai.types.chat.ChatCompletionMessage(
                    content="aaa",
                    role="assistant",
                    tool_calls=[
                        openai.types.chat.ChatCompletionMessageFunctionToolCall(
                            id="id123",
                            function=openai.types.chat.chat_completion_message_function_tool_call.Function(
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
        response_body = (data_dir / "openai.chat.stream.txt").read_text(encoding="utf-8").split("\r\n\r\n", 1)[-1]
        return flask.Response(response_body.split("\r\n"), content_type="text/event-stream")

    with pytilpack.flask.run(app):
        response = openai.OpenAI(api_key="sk-dummy", base_url="http://localhost:5000/v1").chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "1+1=?"}],
            stream=True,
        )
        actual = pytilpack.openai.gather_chunks(response, strict=True)
        expected = openai.types.chat.ChatCompletion(
            id="chatcmpl-9LkPsGgzcOKvsoNpPxy722wmnc8Ij",
            choices=[
                openai.types.chat.chat_completion.Choice(
                    finish_reason="stop",
                    index=0,
                    message=openai.types.chat.ChatCompletionMessage(content="1+1=2", role="assistant"),
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
        response_body = (data_dir / "openai.chat.function1.txt").read_text(encoding="utf-8").split("\r\n\r\n", 1)[-1]
        return flask.Response(response_body.split("\r\n"), content_type="text/event-stream")

    with pytilpack.flask.run(app):
        response = openai.OpenAI(api_key="sk-dummy", base_url="http://localhost:5000/v1").chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "1+1=?"}],
            stream=True,
        )
        actual = pytilpack.openai.gather_chunks(response, strict=True)
        expected = openai.types.chat.ChatCompletion(
            id="chatcmpl-9Lkf3AWNcFV03tyCd5LaAXb2xgZ65",
            choices=[
                openai.types.chat.chat_completion.Choice(
                    finish_reason="tool_calls",
                    index=0,
                    message=openai.types.chat.ChatCompletionMessage(
                        role="assistant",
                        tool_calls=[
                            openai.types.chat.ChatCompletionMessageFunctionToolCall(
                                id="call_flA5AHMfQwJYLsdQFXSk81YA",
                                function=openai.types.chat.chat_completion_message_function_tool_call.Function(
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
        response_body = (data_dir / "openai.chat.function2.txt").read_text(encoding="utf-8").split("\r\n\r\n", 1)[-1]
        return flask.Response(response_body.split("\r\n"), content_type="text/event-stream")

    with pytilpack.flask.run(app):
        response = openai.OpenAI(api_key="sk-dummy", base_url="http://localhost:5000/v1").chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "1+1=?"}],
            stream=True,
        )
        actual = pytilpack.openai.gather_chunks(response, strict=True)
        expected = openai.types.chat.ChatCompletion(
            id="chatcmpl-9LkecCMw4qvicGMfOU00PBHbVbpNL",
            choices=[
                openai.types.chat.chat_completion.Choice(
                    finish_reason="stop",
                    index=0,
                    message=openai.types.chat.ChatCompletionMessage(content="The result of 1 + 1 is 789.", role="assistant"),
                )
            ],
            created=1714971254,
            model="gpt-3.5-turbo-0125",
            object="chat.completion",
            system_fingerprint="fp_3b956da36b",
        )
        assert actual.model_dump() == expected.model_dump()


def test_gather_events_basic():
    """gather_eventsのテスト(基本的なテキスト出力)。"""
    events = [
        openai.types.responses.ResponseCreatedEvent(
            type="response.created",
            sequence_number=0,
            response=openai.types.responses.Response(
                id="resp_001",
                created_at=1234567890.0,
                model="gpt-4o",
                object="response",
                output=[],
                parallel_tool_calls=False,
                tool_choice="auto",
                tools=[],
            ),
        ),
        openai.types.responses.ResponseOutputItemAddedEvent(
            type="response.output_item.added",
            sequence_number=1,
            output_index=0,
            item=openai.types.responses.ResponseOutputMessage(
                id="msg_001",
                type="message",
                role="assistant",
                status="in_progress",
                content=[],
            ),
        ),
        openai.types.responses.ResponseContentPartAddedEvent(
            type="response.content_part.added",
            sequence_number=2,
            output_index=0,
            item_id="msg_001",
            content_index=0,
            part=openai.types.responses.ResponseOutputText(
                type="output_text",
                text="",
                annotations=[],
            ),
        ),
        openai.types.responses.ResponseTextDeltaEvent(
            type="response.output_text.delta",
            sequence_number=3,
            output_index=0,
            item_id="msg_001",
            content_index=0,
            delta="Hello",
            logprobs=[],
        ),
        openai.types.responses.ResponseTextDeltaEvent(
            type="response.output_text.delta",
            sequence_number=4,
            output_index=0,
            item_id="msg_001",
            content_index=0,
            delta=" world",
            logprobs=[],
        ),
        openai.types.responses.ResponseTextDoneEvent(
            type="response.output_text.done",
            sequence_number=5,
            output_index=0,
            item_id="msg_001",
            content_index=0,
            text="Hello world",
            logprobs=[],
        ),
        openai.types.responses.ResponseCompletedEvent(
            type="response.completed",
            sequence_number=6,
            response=openai.types.responses.Response(
                id="resp_001",
                created_at=1234567890.0,
                model="gpt-4o",
                object="response",
                output=[
                    openai.types.responses.ResponseOutputMessage(
                        id="msg_001",
                        type="message",
                        role="assistant",
                        status="completed",
                        content=[
                            openai.types.responses.ResponseOutputText(
                                type="output_text",
                                text="Hello world",
                                annotations=[],
                            )
                        ],
                    )
                ],
                parallel_tool_calls=False,
                tool_choice="auto",
                tools=[],
            ),
        ),
    ]
    actual = pytilpack.openai.gather_events(events, strict=True)  # type: ignore[arg-type]
    assert actual.id == "resp_001"
    assert actual.model == "gpt-4o"
    assert len(actual.output) == 1
    assert actual.output[0].type == "message"
    assert actual.output[0].role == "assistant"
    assert len(actual.output[0].content) == 1
    assert actual.output[0].content[0].type == "output_text"
    assert actual.output[0].content[0].text == "Hello world"


def test_gather_events_function_call():
    """gather_eventsのテスト(関数呼び出し)。"""
    events = [
        openai.types.responses.ResponseCreatedEvent(
            type="response.created",
            sequence_number=0,
            response=openai.types.responses.Response(
                id="resp_002",
                created_at=1234567890.0,
                model="gpt-4o",
                object="response",
                output=[],
                parallel_tool_calls=False,
                tool_choice="auto",
                tools=[],
            ),
        ),
        openai.types.responses.ResponseOutputItemAddedEvent(
            type="response.output_item.added",
            sequence_number=1,
            output_index=0,
            item=openai.types.responses.ResponseFunctionToolCall(
                call_id="call_001",
                type="function_call",
                name="get_weather",
                arguments="",
            ),
        ),
        openai.types.responses.ResponseFunctionCallArgumentsDeltaEvent(
            type="response.function_call_arguments.delta",
            sequence_number=2,
            output_index=0,
            item_id="call_001",
            delta='{"location":',
        ),
        openai.types.responses.ResponseFunctionCallArgumentsDeltaEvent(
            type="response.function_call_arguments.delta",
            sequence_number=3,
            output_index=0,
            item_id="call_001",
            delta='"Tokyo"}',
        ),
        openai.types.responses.ResponseFunctionCallArgumentsDoneEvent(
            type="response.function_call_arguments.done",
            sequence_number=4,
            output_index=0,
            item_id="call_001",
            name="get_weather",
            arguments='{"location":"Tokyo"}',
        ),
        openai.types.responses.ResponseCompletedEvent(
            type="response.completed",
            sequence_number=5,
            response=openai.types.responses.Response(
                id="resp_002",
                created_at=1234567890.0,
                model="gpt-4o",
                object="response",
                output=[
                    openai.types.responses.ResponseFunctionToolCall(
                        call_id="call_001",
                        type="function_call",
                        name="get_weather",
                        arguments='{"location":"Tokyo"}',
                    )
                ],
                parallel_tool_calls=False,
                tool_choice="auto",
                tools=[],
            ),
        ),
    ]
    actual = pytilpack.openai.gather_events(events, strict=True)  # type: ignore[arg-type]
    assert actual.id == "resp_002"
    assert len(actual.output) == 1
    assert actual.output[0].type == "function_call"
    assert actual.output[0].name == "get_weather"
    assert actual.output[0].arguments == '{"location":"Tokyo"}'


def test_gather_events_empty():
    """gather_eventsのテスト(空のイベントリスト)。"""
    events: list[openai.types.responses.ResponseStreamEvent] = []
    actual = pytilpack.openai.gather_events(events, strict=True)  # type: ignore[arg-type]
    assert actual.id == ""
    assert len(actual.output) == 0


def test_gather_events_without_completed():
    """gather_eventsのテスト(response.completedイベントが無い場合)。"""
    events = [
        openai.types.responses.ResponseCreatedEvent(
            type="response.created",
            sequence_number=0,
            response=openai.types.responses.Response(
                id="resp_003",
                created_at=1234567890.0,
                model="gpt-4o",
                object="response",
                output=[],
                parallel_tool_calls=False,
                tool_choice="auto",
                tools=[],
            ),
        ),
        openai.types.responses.ResponseOutputItemAddedEvent(
            type="response.output_item.added",
            sequence_number=1,
            output_index=0,
            item=openai.types.responses.ResponseOutputMessage(
                id="msg_001",
                type="message",
                role="assistant",
                status="in_progress",
                content=[],
            ),
        ),
        openai.types.responses.ResponseContentPartAddedEvent(
            type="response.content_part.added",
            sequence_number=2,
            output_index=0,
            item_id="msg_001",
            content_index=0,
            part=openai.types.responses.ResponseOutputText(
                type="output_text",
                text="",
                annotations=[],
            ),
        ),
        openai.types.responses.ResponseTextDeltaEvent(
            type="response.output_text.delta",
            sequence_number=3,
            output_index=0,
            item_id="msg_001",
            content_index=0,
            delta="Test",
            logprobs=[],
        ),
    ]
    actual = pytilpack.openai.gather_events(events, strict=True)  # type: ignore[arg-type]
    assert actual.id == "resp_003"
    assert len(actual.output) == 1
    assert actual.output[0].type == "message"
    assert len(actual.output[0].content) == 1
    assert actual.output[0].content[0].type == "output_text"
    assert actual.output[0].content[0].text == "Test"
