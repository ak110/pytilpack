"""Flaskアサーションのテスト。"""

import pathlib
import typing

import flask
import flask.testing
import pytest

import pytilpack.flask


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
