"""テストコード。"""

import fastapi
import fastapi.testclient
import pytest

import pytilpack.fastapi_


@pytest.fixture(name="app")
def _app():
    app = fastapi.FastAPI()

    @app.get("/403")
    def forbidden():
        raise fastapi.HTTPException(status_code=403)

    @app.get("/html")
    def html():
        return fastapi.responses.HTMLResponse(
            "<!doctype html><p>hello</p>", status_code=200
        )

    @app.get("/html-invalid")
    def html_invalid():
        return fastapi.responses.HTMLResponse(
            "<!doctype html><body>hello</form></body>", status_code=200
        )

    @app.get("/json")
    def json():
        return {"hello": "world"}

    @app.get("/json-invalid")
    def json_invalid():
        return fastapi.responses.JSONResponse('{hello: "world"}', status_code=200)

    @app.get("/xml")
    def xml():
        return fastapi.responses.Response(
            "<root><hello>world</hello></root>", status_code=200, media_type="text/xml"
        )

    @app.get("/xml-invalid")
    def xml_invalid():
        return fastapi.responses.Response(
            "<root>hello & world</root>", status_code=200, media_type="application/xml"
        )

    return app


@pytest.fixture(name="client")
def _client(app):
    return fastapi.testclient.TestClient(app)


def test_assert_bytes(client, tmp_path):
    """bytesアサーションのテスト。"""
    response = client.get("/html")
    pytilpack.fastapi_.assert_bytes(response)
    pytilpack.fastapi_.assert_bytes(response, content_type="text/html")

    response = client.get("/403")
    pytilpack.fastapi_.assert_bytes(response, 403)
    with pytest.raises(AssertionError):
        pytilpack.fastapi_.assert_bytes(response)
    with pytest.raises(AssertionError):
        pytilpack.fastapi_.assert_bytes(response, content_type="application/json")


def test_assert_html(client, tmp_path):
    """HTMLアサーションのテスト。"""
    response = client.get("/html")
    pytilpack.fastapi_.assert_html(response)
    pytilpack.fastapi_.assert_html(response, content_type="text/html")
    pytilpack.fastapi_.assert_html(response, tmp_path=tmp_path)

    # strictモードでのテスト
    pytilpack.fastapi_.assert_html(response, strict=False)
    with pytest.raises(AssertionError):
        pytilpack.fastapi_.assert_html(response, strict=True)

    response = client.get("/html-invalid")
    with pytest.raises(AssertionError):
        pytilpack.fastapi_.assert_html(response)

    response = client.get("/403")
    pytilpack.fastapi_.assert_html(response, 403)
    with pytest.raises(AssertionError):
        pytilpack.fastapi_.assert_html(response)


def test_assert_json(client, tmp_path):
    """JSONアサーションのテスト。"""
    response = client.get("/json")
    pytilpack.fastapi_.assert_json(response)
    pytilpack.fastapi_.assert_json(response, content_type="application/json")

    response = client.get("/json-invalid")
    with pytest.raises(AssertionError):
        pytilpack.fastapi_.assert_json(response)

    response = client.get("/html")
    with pytest.raises(AssertionError):
        pytilpack.fastapi_.assert_json(response)
    with pytest.raises(AssertionError):
        pytilpack.fastapi_.assert_json(response, content_type="application/json")


def test_assert_xml(client, tmp_path):
    """XMLアサーションのテスト。"""
    response = client.get("/xml")
    pytilpack.fastapi_.assert_xml(response)
    pytilpack.fastapi_.assert_xml(response, content_type="text/xml")

    response = client.get("/xml-invalid")
    with pytest.raises(AssertionError):
        pytilpack.fastapi_.assert_xml(response)

    response = client.get("/html")
    with pytest.raises(AssertionError):
        pytilpack.fastapi_.assert_xml(response)
