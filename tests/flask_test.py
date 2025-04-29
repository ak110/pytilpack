"""テストコード。"""

import flask
import pytest

import pytilpack.flask_


@pytest.fixture(name="app")
def _app():
    app = flask.Flask(__name__)

    @app.route("/403")
    def forbidden():
        flask.abort(403)

    @app.route("/html")
    def html():
        return "<!doctype html><p>hello</p>", 200, {"Content-Type": "text/html"}

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
def _client(app):
    with app.test_client() as client:
        yield client


def test_assert_bytes(client, tmp_path):
    """bytesアサーションのテスト。"""
    response = client.get("/html")
    pytilpack.flask_.assert_bytes(response)
    pytilpack.flask_.assert_bytes(response, content_type="text/html")

    response = client.get("/403")
    pytilpack.flask_.assert_bytes(response, 403)
    with pytest.raises(AssertionError):
        pytilpack.flask_.assert_bytes(response)
    with pytest.raises(AssertionError):
        pytilpack.flask_.assert_bytes(response, content_type="application/json")


def test_assert_html(client, tmp_path):
    """HTMLアサーションのテスト。"""
    response = client.get("/html")
    pytilpack.flask_.assert_html(response)
    pytilpack.flask_.assert_html(response, content_type="text/html")
    pytilpack.flask_.assert_html(response, tmp_path=tmp_path)

    # strictモードでのテスト
    response = client.get("/html-invalid")
    with pytest.raises(AssertionError):
        pytilpack.flask_.assert_html(response, strict=True)

    # 通常のテスト
    response = client.get("/html-invalid")
    with pytest.raises(AssertionError):
        pytilpack.flask_.assert_html(response)

    response = client.get("/403")
    pytilpack.flask_.assert_html(response, 403)
    with pytest.raises(AssertionError):
        pytilpack.flask_.assert_html(response)


def test_assert_json(client, tmp_path):
    """JSONアサーションのテスト。"""
    response = client.get("/json")
    pytilpack.flask_.assert_json(response)
    pytilpack.flask_.assert_json(response, content_type="application/json")

    response = client.get("/json-invalid")
    with pytest.raises(AssertionError):
        pytilpack.flask_.assert_json(response)

    response = client.get("/html")
    with pytest.raises(AssertionError):
        pytilpack.flask_.assert_json(response)
    with pytest.raises(AssertionError):
        pytilpack.flask_.assert_json(response, content_type="application/json")


def test_assert_xml(client, tmp_path):
    """XMLアサーションのテスト。"""
    response = client.get("/xml")
    pytilpack.flask_.assert_xml(response)
    pytilpack.flask_.assert_xml(response, content_type="text/xml")

    response = client.get("/xml-invalid")
    with pytest.raises(AssertionError):
        pytilpack.flask_.assert_xml(response)

    response = client.get("/html")
    with pytest.raises(AssertionError):
        pytilpack.flask_.assert_xml(response)
