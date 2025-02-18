"""テストコード。"""

import flask
import pytest

import pytilpack.flask_


def test_generate_secret_key(tmp_path):
    path = tmp_path / "secret_key"
    assert not path.exists()
    secret_key1 = pytilpack.flask_.generate_secret_key(path)
    assert path.exists()
    secret_key2 = pytilpack.flask_.generate_secret_key(path)
    assert secret_key1 == secret_key2


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
            "<!doctype html><body><form>hello</body>",
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


def test_assert_html(client):
    response = client.get("/html")
    pytilpack.flask_.assert_html(response)

    response = client.get("/html-invalid")
    with pytest.raises(AssertionError):
        pytilpack.flask_.assert_html(response)

    response = client.get("/403")
    pytilpack.flask_.assert_html(response, 403)
    with pytest.raises(AssertionError):
        pytilpack.flask_.assert_html(response)


def test_assert_json(client):
    response = client.get("/json")
    pytilpack.flask_.assert_json(response)

    response = client.get("/json-invalid")
    with pytest.raises(AssertionError):
        pytilpack.flask_.assert_json(response)

    response = client.get("/html")
    with pytest.raises(AssertionError):
        pytilpack.flask_.assert_json(response)


def test_assert_xml(client):
    response = client.get("/xml")
    pytilpack.flask_.assert_xml(response, content_type="text/xml")

    response = client.get("/xml-invalid")
    with pytest.raises(AssertionError):
        pytilpack.flask_.assert_xml(response)

    response = client.get("/html")
    with pytest.raises(AssertionError):
        pytilpack.flask_.assert_xml(response)
