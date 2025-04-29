"""テストコード。"""

import pytest
import pytest_asyncio
import quart

import pytilpack.quart_


@pytest_asyncio.fixture(name="app", scope="module")
async def _app():
    app = quart.Quart(__name__)

    @app.route("/403")
    async def forbidden():
        quart.abort(403)

    @app.route("/html")
    async def html():
        return "<!doctype html><p>hello</p>", 200, {"Content-Type": "text/html"}

    @app.route("/html-invalid")
    async def html_invalid():
        return (
            "<!doctype html><body>hello</form></body>",
            200,
            {"Content-Type": "text/html"},
        )

    @app.route("/json")
    async def json():
        return {"hello": "world"}

    @app.route("/json-invalid")
    async def json_invalid():
        return '{hello: "world"}', 200, {"Content-Type": "application/json"}

    @app.route("/xml")
    async def xml():
        return "<root><hello>world</hello></root>", 200, {"Content-Type": "text/xml"}

    @app.route("/xml-invalid")
    async def xml_invalid():
        return "<root>hello & world</root>", 200, {"Content-Type": "application/xml"}

    async with app.app_context():
        yield app


@pytest_asyncio.fixture(name="client", scope="function")
async def _client(app: quart.Quart):
    async with app.test_client() as client:
        yield client


async def test_assert_bytes(client: quart.testing.client.QuartClient, tmp_path) -> None:
    """bytesアサーションのテスト。"""
    response = await client.get("/html")
    await pytilpack.quart_.assert_bytes(response)
    await pytilpack.quart_.assert_bytes(response, content_type="text/html")

    response = await client.get("/403")
    await pytilpack.quart_.assert_bytes(response, 403)
    with pytest.raises(AssertionError):
        await pytilpack.quart_.assert_bytes(response)
    with pytest.raises(AssertionError):
        await pytilpack.quart_.assert_bytes(response, content_type="application/json")


async def test_assert_html(client: quart.testing.client.QuartClient, tmp_path) -> None:
    """HTMLアサーションのテスト。"""
    response = await client.get("/html")
    await pytilpack.quart_.assert_html(response)
    await pytilpack.quart_.assert_html(response, content_type="text/html")
    await pytilpack.quart_.assert_html(response, tmp_path=tmp_path)

    # strictモードでのテスト
    response = await client.get("/html-invalid")
    with pytest.raises(AssertionError):
        await pytilpack.quart_.assert_html(response, strict=True)

    # 通常のテスト
    response = await client.get("/html-invalid")
    with pytest.raises(AssertionError):
        await pytilpack.quart_.assert_html(response)

    response = await client.get("/403")
    await pytilpack.quart_.assert_html(response, 403)
    with pytest.raises(AssertionError):
        await pytilpack.quart_.assert_html(response)


async def test_assert_json(client: quart.testing.client.QuartClient, tmp_path) -> None:
    """JSONアサーションのテスト。"""
    response = await client.get("/json")
    await pytilpack.quart_.assert_json(response)
    await pytilpack.quart_.assert_json(response, content_type="application/json")

    response = await client.get("/json-invalid")
    with pytest.raises(AssertionError):
        await pytilpack.quart_.assert_json(response)

    response = await client.get("/html")
    with pytest.raises(AssertionError):
        await pytilpack.quart_.assert_json(response)
    with pytest.raises(AssertionError):
        await pytilpack.quart_.assert_json(response, content_type="application/json")


async def test_assert_xml(client: quart.testing.client.QuartClient, tmp_path) -> None:
    """XMLアサーションのテスト。"""
    response = await client.get("/xml")
    await pytilpack.quart_.assert_xml(response)
    await pytilpack.quart_.assert_xml(response, content_type="text/xml")

    response = await client.get("/xml-invalid")
    with pytest.raises(AssertionError):
        await pytilpack.quart_.assert_xml(response)

    response = await client.get("/html")
    with pytest.raises(AssertionError):
        await pytilpack.quart_.assert_xml(response)


async def test_proxy_fix() -> None:
    """ProxyFixのテスト。"""
    app = quart.Quart(__name__)
    app.config["APPLICATION_ROOT"] = "/"
    app.config["SESSION_COOKIE_PATH"] = "/"

    @app.route("/")
    async def index():
        return {
            "client": quart.request.remote_addr,
            "scheme": quart.request.scheme,
            "host": quart.request.headers.get("Host"),
            "root_path": quart.request.blueprint,
        }

    app.asgi_app = pytilpack.quart_.ProxyFix(app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)  # type: ignore

    async with app.app_context(), app.test_client() as client:
        # X-Forwarded-For
        headers = {"X-Forwarded-For": "192.168.1.2, 192.168.1.1"}
        response = await client.get("/", headers=headers)
        data = await pytilpack.quart_.assert_json(response)
        # assert data["client"] == "192.168.1.1"
        assert data["client"] == "<local>"

        # X-Forwarded-Proto
        headers = {"X-Forwarded-Proto": "https"}
        response = await client.get("/", headers=headers)
        data = await pytilpack.quart_.assert_json(response)
        assert data["scheme"] == "https"

        # X-Forwarded-Host
        headers = {"X-Forwarded-Host": "example.com:8443"}
        response = await client.get("/", headers=headers)
        data = await pytilpack.quart_.assert_json(response)
        assert data["host"] == "example.com:8443"

        # X-Forwarded-Prefix
        headers = {"X-Forwarded-Prefix": "/prefix"}
        response = await client.get("/", headers=headers)
        data = await pytilpack.quart_.assert_json(response)
        assert app.config["APPLICATION_ROOT"] == "/prefix"
        assert app.config["SESSION_COOKIE_PATH"] == "/prefix/"
