"""Flaskアサーションのテスト。"""

import pathlib
import typing

import flask
import flask.testing
import pytest

import pytilpack.flask
import tests.web_test


@pytest.fixture(name="app")
def _app() -> typing.Generator[flask.Flask, None, None]:
    app = flask.Flask(__name__)

    @app.route("/403")
    def forbidden():
        flask.abort(403)

    @app.route("/html")
    def html():
        return "<!doctype html><p>hello", 200, {"Content-Type": "text/html"}

    @app.route("/html-invalid")
    def html_invalid():
        return (
            "<!doctype html><body>hello</form></body>",
            200,
            {"Content-Type": "text/html"},
        )

    @app.post("/html-case")
    def html_case():
        return flask.Response(flask.request.get_data(), content_type="text/html; charset=utf-8")

    @app.route("/json")
    def json():
        return flask.jsonify({"hello": "world"})

    @app.route("/json-invalid")
    def json_invalid():
        return '{hello: "world"}', 200, {"Content-Type": "application/json"}

    @app.route("/xml")
    def xml():
        return "<root><hello>world</hello></root>", 200, {"Content-Type": "text/xml"}

    @app.route("/xml-invalid")
    def xml_invalid():
        return "<root>hello & world</root>", 200, {"Content-Type": "application/xml"}

    @app.route("/sse")
    def sse():
        return flask.Response(iter(["data: hello\n\n"]), content_type="text/event-stream")

    yield app


@pytest.fixture(name="client")
def _client(app) -> typing.Generator[flask.testing.FlaskClient, None, None]:
    with app.test_client() as client:
        yield client


def test_assert_bytes(client: flask.testing.FlaskClient) -> None:
    """bytesアサーションのテスト。"""
    response = client.get("/html")
    _ = pytilpack.flask.assert_bytes(response)
    _ = pytilpack.flask.assert_bytes(response, content_type="text/html")

    response = client.get("/403")
    _ = pytilpack.flask.assert_bytes(response, 403)
    with pytest.raises(AssertionError):
        _ = pytilpack.flask.assert_bytes(response)
    with pytest.raises(AssertionError):
        _ = pytilpack.flask.assert_bytes(response, content_type="application/json")


def test_assert_html(client: flask.testing.FlaskClient, tmp_path: pathlib.Path) -> None:
    """HTMLアサーションのテスト。"""
    response = client.get("/html")
    _ = pytilpack.flask.assert_html(response)
    _ = pytilpack.flask.assert_html(response, content_type="text/html")
    _ = pytilpack.flask.assert_html(response, tmp_path=tmp_path)
    _ = pytilpack.flask.assert_html(response, strict=True)

    response = client.get("/403")
    _ = pytilpack.flask.assert_html(response, 403)
    with pytest.raises(AssertionError):
        _ = pytilpack.flask.assert_html(response)

    response = client.get("/html-invalid")
    with pytest.raises(AssertionError):
        _ = pytilpack.flask.assert_html(response, strict=True)


@pytest.mark.parametrize("fragment", tests.web_test.HTML_VALID_CASES)
def test_assert_html_current_syntax(client: flask.testing.FlaskClient, fragment: str, caplog: pytest.LogCaptureFixture) -> None:
    """現行HTMLの正例をレスポンスbytesから検査してボディを返す。"""
    html = f"<!doctype html><meta charset='utf-8'><title>t</title>\n{fragment}"
    response = client.post("/html-case", data=html.encode())
    for strict in (True, False):
        assert pytilpack.flask.assert_html(response, strict=strict) == html
    assert not [record for record in caplog.records if record.name == "pytilpack.web" and "HTMLエラー:" in record.message]


@pytest.mark.parametrize("fragment,expected", tests.web_test.HTML_INVALID_CASES)
def test_assert_html_diagnostics_retained(
    client: flask.testing.FlaskClient, fragment: str, expected: tuple[str, ...], caplog: pytest.LogCaptureFixture
) -> None:
    """レスポンスbytesの構文診断を通知し、警告時もボディを返す。"""
    html = f"<!doctype html><meta charset='utf-8'><title>t</title>\n{fragment}"
    response = client.post("/html-case", data=html.encode())
    with pytest.raises(AssertionError) as exc_info:
        pytilpack.flask.assert_html(response, strict=True)
    caplog.clear()
    assert pytilpack.flask.assert_html(response, strict=False) == html
    # AssertBlockが短縮した見出しに加え、例外チェーンに残る構文診断を確認する。
    assert exc_info.value.__cause__ is not None
    for diagnostic in expected:
        assert diagnostic in str(exc_info.value.__cause__).lower()
        assert diagnostic in caplog.text.lower()


def test_assert_json(client: flask.testing.FlaskClient) -> None:
    """JSONアサーションのテスト。"""
    response = client.get("/json")
    _ = pytilpack.flask.assert_json(response)

    response = client.get("/json-invalid")
    with pytest.raises(AssertionError):
        _ = pytilpack.flask.assert_json(response)

    response = client.get("/html")
    with pytest.raises(AssertionError):
        _ = pytilpack.flask.assert_json(response)


def test_assert_xml(client: flask.testing.FlaskClient) -> None:
    """XMLアサーションのテスト。"""
    response = client.get("/xml")
    _ = pytilpack.flask.assert_xml(response)
    _ = pytilpack.flask.assert_xml(response, content_type="text/xml")

    response = client.get("/xml-invalid")
    with pytest.raises(AssertionError):
        _ = pytilpack.flask.assert_xml(response)

    response = client.get("/html")
    with pytest.raises(AssertionError):
        _ = pytilpack.flask.assert_xml(response)


def test_assert_sse(client: flask.testing.FlaskClient) -> None:
    """SSEアサーションのテスト。"""
    response = client.get("/sse")
    _ = pytilpack.flask.assert_sse(response)

    response = client.get("/403")
    with pytest.raises(AssertionError):
        _ = pytilpack.flask.assert_sse(response)

    response = client.get("/html")
    with pytest.raises(AssertionError):
        _ = pytilpack.flask.assert_sse(response)


def test_assert_response(client: flask.testing.FlaskClient) -> None:
    """レスポンスアサーションのテスト。"""
    response = client.get("/html")
    _ = pytilpack.flask.assert_response(response)

    response = client.get("/403")
    with pytest.raises(AssertionError):
        _ = pytilpack.flask.assert_response(response)
