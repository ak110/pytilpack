"""Quartアサーションのテスト。"""

import pathlib
import typing

import pytest
import pytest_asyncio
import quart
import quart.typing

import pytilpack.quart


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
