"""Quartアサーションのテスト。"""

import pathlib
import typing

import pytest
import pytest_asyncio
import quart
import quart.typing

import pytilpack.quart
import pytilpack.sse
import tests.web_test


@pytest.fixture(name="app")
def _app() -> typing.Generator[quart.Quart, None, None]:
    app = quart.Quart(__name__)

    @app.route("/403")
    async def forbidden():
        quart.abort(403)

    @app.route("/html")
    async def html():
        return "<!doctype html><p>hello", 200, {"Content-Type": "text/html"}

    @app.route("/html-invalid")
    async def html_invalid():
        return (
            "<!doctype html><body>hello</form></body>",
            200,
            {"Content-Type": "text/html"},
        )

    @app.post("/html-case")
    async def html_case():
        return quart.Response(await quart.request.get_data(), content_type="text/html; charset=utf-8")

    @app.route("/json")
    async def json():
        return quart.jsonify({"hello": "world"})

    @app.route("/json-invalid")
    async def json_invalid():
        return '{hello: "world"}', 200, {"Content-Type": "application/json"}

    @app.route("/xml")
    async def xml():
        return "<root><hello>world</hello></root>", 200, {"Content-Type": "text/xml"}

    @app.route("/xml-invalid")
    async def xml_invalid():
        return "<root>hello & world</root>", 200, {"Content-Type": "application/xml"}

    @app.route("/sse")
    async def sse():
        @pytilpack.sse.generator()
        async def generator():
            yield "data: hello\n\n"

        return quart.Response(
            generator(),
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    yield app


@pytest_asyncio.fixture(name="client")
async def _client(
    app: quart.Quart,
) -> typing.AsyncGenerator[quart.typing.TestClientProtocol, None]:
    async with app.test_client() as client:
        yield client


@pytest.mark.asyncio
async def test_assert_bytes(client: quart.typing.TestClientProtocol) -> None:
    """bytesアサーションのテスト。"""
    response = await client.get("/html")
    _ = await pytilpack.quart.assert_bytes(response)
    _ = await pytilpack.quart.assert_bytes(response, content_type="text/html")

    response = await client.get("/403")
    _ = await pytilpack.quart.assert_bytes(response, 403)
    with pytest.raises(AssertionError):
        _ = await pytilpack.quart.assert_bytes(response)
    with pytest.raises(AssertionError):
        _ = await pytilpack.quart.assert_bytes(response, content_type="application/json")


@pytest.mark.asyncio
async def test_assert_html(client: quart.typing.TestClientProtocol, tmp_path: pathlib.Path) -> None:
    """HTMLアサーションのテスト。"""
    response = await client.get("/html")
    _ = await pytilpack.quart.assert_html(response)
    _ = await pytilpack.quart.assert_html(response, content_type="text/html")
    _ = await pytilpack.quart.assert_html(response, tmp_path=tmp_path)
    _ = await pytilpack.quart.assert_html(response, strict=True)

    response = await client.get("/403")
    _ = await pytilpack.quart.assert_html(response, 403)
    with pytest.raises(AssertionError):
        _ = await pytilpack.quart.assert_html(response)

    response = await client.get("/html-invalid")
    with pytest.raises(AssertionError):
        _ = await pytilpack.quart.assert_html(response, strict=True)


@pytest.mark.parametrize("fragment", tests.web_test.HTML_VALID_CASES)
@pytest.mark.asyncio
async def test_assert_html_current_syntax(
    client: quart.typing.TestClientProtocol, fragment: str, caplog: pytest.LogCaptureFixture
) -> None:
    """現行HTMLの正例をレスポンスbytesから検査してボディを返す。"""
    html = f"<!doctype html><meta charset='utf-8'><title>t</title>\n{fragment}"
    response = await client.post("/html-case", data=html.encode())
    for strict in (True, False):
        assert await pytilpack.quart.assert_html(response, strict=strict) == html
    assert not [record for record in caplog.records if record.name == "pytilpack.web" and "HTMLエラー:" in record.message]


@pytest.mark.parametrize("fragment,expected", tests.web_test.HTML_INVALID_CASES)
@pytest.mark.asyncio
async def test_assert_html_diagnostics_retained(
    client: quart.typing.TestClientProtocol, fragment: str, expected: tuple[str, ...], caplog: pytest.LogCaptureFixture
) -> None:
    """レスポンスbytesの構文診断を通知し、警告時もボディを返す。"""
    html = f"<!doctype html><meta charset='utf-8'><title>t</title>\n{fragment}"
    response = await client.post("/html-case", data=html.encode())
    with pytest.raises(AssertionError) as exc_info:
        await pytilpack.quart.assert_html(response, strict=True)
    caplog.clear()
    assert await pytilpack.quart.assert_html(response, strict=False) == html
    # AssertBlockが短縮した見出しに加え、例外チェーンに残る構文診断を確認する。
    assert exc_info.value.__cause__ is not None
    for diagnostic in expected:
        assert diagnostic in str(exc_info.value.__cause__).lower()
        assert diagnostic in caplog.text.lower()


@pytest.mark.asyncio
async def test_assert_json(client: quart.typing.TestClientProtocol) -> None:
    """JSONアサーションのテスト。"""
    response = await client.get("/json")
    _ = await pytilpack.quart.assert_json(response)

    response = await client.get("/json-invalid")
    with pytest.raises(AssertionError):
        _ = await pytilpack.quart.assert_json(response)

    response = await client.get("/html")
    with pytest.raises(AssertionError):
        _ = await pytilpack.quart.assert_json(response)


@pytest.mark.asyncio
async def test_assert_xml(client: quart.typing.TestClientProtocol) -> None:
    """XMLアサーションのテスト。"""
    response = await client.get("/xml")
    _ = await pytilpack.quart.assert_xml(response)
    _ = await pytilpack.quart.assert_xml(response, content_type="text/xml")

    response = await client.get("/xml-invalid")
    with pytest.raises(AssertionError):
        _ = await pytilpack.quart.assert_xml(response)

    response = await client.get("/html")
    with pytest.raises(AssertionError):
        _ = await pytilpack.quart.assert_xml(response)


@pytest.mark.asyncio
async def test_assert_sse(client: quart.typing.TestClientProtocol) -> None:
    """SSEアサーションのテスト。"""
    response = await client.get("/sse")
    _ = await pytilpack.quart.assert_sse(response)

    response = await client.get("/403")
    with pytest.raises(AssertionError):
        _ = await pytilpack.quart.assert_sse(response)

    response = await client.get("/html")
    with pytest.raises(AssertionError):
        _ = await pytilpack.quart.assert_sse(response)


@pytest.mark.asyncio
async def test_assert_response(client: quart.typing.TestClientProtocol) -> None:
    """レスポンスアサーションのテスト。"""
    response = await client.get("/html")
    _ = await pytilpack.quart.assert_response(response)

    response = await client.get("/403")
    with pytest.raises(AssertionError):
        _ = await pytilpack.quart.assert_response(response)
