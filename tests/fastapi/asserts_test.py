"""FastAPIアサーションのテスト。"""

import pathlib

import fastapi
import fastapi.responses
import fastapi.testclient
import pytest

import pytilpack.fastapi


@pytest.fixture(name="app")
def _app() -> fastapi.FastAPI:
    app = fastapi.FastAPI()

    @app.get("/403")
    def forbidden():
        return fastapi.responses.HTMLResponse("403 Error", status_code=403, media_type="text/html")

    @app.get("/html")
    def html():
        return fastapi.responses.HTMLResponse("<!doctype html><p>hello", status_code=200, media_type="text/html")

    @app.get("/html-invalid")
    def html_invalid():
        return fastapi.responses.HTMLResponse(
            "<!doctype html><body>hello</form></body>",
            status_code=200,
            media_type="text/html",
        )

    @app.get("/json")
    def json():
        return {"hello": "world"}

    @app.get("/json-invalid")
    def json_invalid():
        return fastapi.responses.Response('{hello: "world"}', status_code=200, media_type="application/json")

    @app.get("/xml")
    def xml():
        return fastapi.responses.Response("<root><hello>world</hello></root>", status_code=200, media_type="text/xml")

    @app.get("/xml-invalid")
    def xml_invalid():
        return fastapi.responses.Response("<root>hello & world</root>", status_code=200, media_type="application/xml")

    return app


@pytest.fixture(name="client")
def _client(app: fastapi.FastAPI) -> fastapi.testclient.TestClient:
    return fastapi.testclient.TestClient(app)


def test_assert_bytes(client: fastapi.testclient.TestClient):
    """bytesアサーションのテスト。"""
    response = client.get("/html")
    _ = pytilpack.fastapi.assert_bytes(response)
    _ = pytilpack.fastapi.assert_bytes(response, content_type="text/html")

    response = client.get("/403")
    _ = pytilpack.fastapi.assert_bytes(response, 403)
    with pytest.raises(AssertionError):
        _ = pytilpack.fastapi.assert_bytes(response)


def test_assert_html(client: fastapi.testclient.TestClient, tmp_path: pathlib.Path) -> None:
    """HTMLアサーションのテスト。"""
    response = client.get("/html")
    _ = pytilpack.fastapi.assert_html(response)
    _ = pytilpack.fastapi.assert_html(response, content_type="text/html")
    _ = pytilpack.fastapi.assert_html(response, tmp_path=tmp_path)
    _ = pytilpack.fastapi.assert_html(response, strict=True)

    response = client.get("/403")
    _ = pytilpack.fastapi.assert_html(response, 403)
    with pytest.raises(AssertionError):
        _ = pytilpack.fastapi.assert_html(response)

    response = client.get("/html-invalid")
    with pytest.raises(AssertionError):
        _ = pytilpack.fastapi.assert_html(response, strict=True)


def test_assert_json(client: fastapi.testclient.TestClient) -> None:
    """JSONアサーションのテスト。"""
    response = client.get("/json")
    _ = pytilpack.fastapi.assert_json(response)

    response = client.get("/json-invalid")
    with pytest.raises(AssertionError):
        _ = pytilpack.fastapi.assert_json(response)

    response = client.get("/html")
    with pytest.raises(AssertionError):
        _ = pytilpack.fastapi.assert_json(response)


def test_assert_xml(client: fastapi.testclient.TestClient) -> None:
    """XMLアサーションのテスト。"""
    response = client.get("/xml")
    _ = pytilpack.fastapi.assert_xml(response)
    _ = pytilpack.fastapi.assert_xml(response, content_type="text/xml")

    response = client.get("/xml-invalid")
    with pytest.raises(AssertionError):
        _ = pytilpack.fastapi.assert_xml(response)

    response = client.get("/html")
    with pytest.raises(AssertionError):
        _ = pytilpack.fastapi.assert_xml(response)
