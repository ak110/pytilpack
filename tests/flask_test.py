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
def _client(app):
    with app.test_client() as client:
        yield client


def test_assert_bytes(client):
    """bytesアサーションのテスト。"""
    response = client.get("/html")
    _ = pytilpack.flask_.assert_bytes(response)
    _ = pytilpack.flask_.assert_bytes(response, content_type="text/html")

    response = client.get("/403")
    _ = pytilpack.flask_.assert_bytes(response, 403)
    with pytest.raises(AssertionError):
        _ = pytilpack.flask_.assert_bytes(response)
    with pytest.raises(AssertionError):
        _ = pytilpack.flask_.assert_bytes(response, content_type="application/json")


def test_assert_html(client, tmp_path):
    """HTMLアサーションのテスト。"""
    response = client.get("/html")
    _ = pytilpack.flask_.assert_html(response)
    _ = pytilpack.flask_.assert_html(response, content_type="text/html")
    _ = pytilpack.flask_.assert_html(response, tmp_path=tmp_path)
    _ = pytilpack.flask_.assert_html(response, strict=True)

    response = client.get("/403")
    _ = pytilpack.flask_.assert_html(response, 403)
    with pytest.raises(AssertionError):
        _ = pytilpack.flask_.assert_html(response)

    response = client.get("/html-invalid")
    with pytest.raises(AssertionError):
        _ = pytilpack.flask_.assert_html(response, strict=True)


def test_assert_json(client):
    """JSONアサーションのテスト。"""
    response = client.get("/json")
    _ = pytilpack.flask_.assert_json(response)

    response = client.get("/json-invalid")
    with pytest.raises(AssertionError):
        _ = pytilpack.flask_.assert_json(response)

    response = client.get("/html")
    with pytest.raises(AssertionError):
        _ = pytilpack.flask_.assert_json(response)


def test_assert_xml(client):
    """XMLアサーションのテスト。"""
    response = client.get("/xml")
    _ = pytilpack.flask_.assert_xml(response)
    _ = pytilpack.flask_.assert_xml(response, content_type="text/xml")

    response = client.get("/xml-invalid")
    with pytest.raises(AssertionError):
        _ = pytilpack.flask_.assert_xml(response)

    response = client.get("/html")
    with pytest.raises(AssertionError):
        _ = pytilpack.flask_.assert_xml(response)


def test_static_url_for(tmp_path):
    """static_url_forのテスト。"""
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    test_file = static_dir / "test.css"
    test_file.write_text("body { color: red; }")
    static_dir_str = str(static_dir)  # Flask requires str for static_folder

    app = flask.Flask(__name__, static_folder=static_dir_str)
    with app.test_request_context():
        # キャッシュバスティングあり
        url = pytilpack.flask_.static_url_for("test.css")
        assert url.startswith("/static/test.css?v=")
        mtime = int(test_file.stat().st_mtime)
        assert f"v={mtime}" in url

        # キャッシュバスティングなし
        url = pytilpack.flask_.static_url_for("test.css", cache_busting=False)
        assert url == "/static/test.css"

        # 存在しないファイル
        url = pytilpack.flask_.static_url_for("notexist.css")
        assert url == "/static/notexist.css"
