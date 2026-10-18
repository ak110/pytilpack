"""FastAPIアサーションのテスト。"""

import pathlib

import fastapi
import fastapi.responses
import fastapi.testclient
import httpx
import pytest

import pytilpack.fastapi
import tests.web_test


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

    @app.post("/html-case")
    async def html_case(request: fastapi.Request):
        return fastapi.responses.HTMLResponse(await request.body())

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

    @app.get("/sse")
    def sse():
        return fastapi.responses.StreamingResponse(iter(["data: hello\n\n"]), media_type="text/event-stream")

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


@pytest.mark.parametrize("fragment", tests.web_test.HTML_VALID_CASES)
def test_assert_html_current_syntax(
    client: fastapi.testclient.TestClient, fragment: str, caplog: pytest.LogCaptureFixture
) -> None:
    """現行HTMLの正例をレスポンスbytesから検査してボディを返す。"""
    html = f"<!doctype html><meta charset='utf-8'><title>t</title>\n{fragment}"
    response = client.post("/html-case", content=html.encode())
    for strict in (True, False):
        assert pytilpack.fastapi.assert_html(response, strict=strict) == html
    assert not [record for record in caplog.records if record.name == "pytilpack.web" and "HTMLエラー:" in record.message]


@pytest.mark.parametrize("fragment,expected", tests.web_test.HTML_INVALID_CASES)
def test_assert_html_diagnostics_retained(
    client: fastapi.testclient.TestClient, fragment: str, expected: tuple[str, ...], caplog: pytest.LogCaptureFixture
) -> None:
    """レスポンスbytesの構文診断を通知し、警告時もボディを返す。"""
    html = f"<!doctype html><meta charset='utf-8'><title>t</title>\n{fragment}"
    response = client.post("/html-case", content=html.encode())
    with pytest.raises(AssertionError) as exc_info:
        pytilpack.fastapi.assert_html(response, strict=True)
    caplog.clear()
    assert pytilpack.fastapi.assert_html(response, strict=False) == html
    # AssertBlockが短縮した見出しに加え、例外チェーンに残る構文診断を確認する。
    assert exc_info.value.__cause__ is not None
    for diagnostic in expected:
        assert diagnostic in str(exc_info.value.__cause__).lower()
        assert diagnostic in caplog.text.lower()


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


def test_assert_sse(client: fastapi.testclient.TestClient) -> None:
    """SSEアサーションのテスト。"""
    response = client.get("/sse")
    _ = pytilpack.fastapi.assert_sse(response)

    response = client.get("/403")
    with pytest.raises(AssertionError):
        _ = pytilpack.fastapi.assert_sse(response)

    response = client.get("/html")
    with pytest.raises(AssertionError):
        _ = pytilpack.fastapi.assert_sse(response)


def test_response_type() -> None:
    """httpxレスポンスが構造的型へ適合することを検証する。"""
    response = httpx.Response(200)
    typed_response: pytilpack.fastapi.ResponseType = response

    assert pytilpack.fastapi.assert_response(typed_response) is response


def test_assert_response(client: fastapi.testclient.TestClient) -> None:
    """レスポンスアサーションのテスト。"""
    response = client.get("/html")
    typed_response: pytilpack.fastapi.ResponseType = response
    assert pytilpack.fastapi.assert_response(typed_response) is response

    response = client.get("/403")
    with pytest.raises(AssertionError):
        _ = pytilpack.fastapi.assert_response(response)
