"""Flask miscのテスト。"""

import pathlib

import flask
import httpx

import pytilpack.flask


def test_static_url_for(tmp_path: pathlib.Path) -> None:
    """static_url_forのテスト。"""
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    test_file = static_dir / "test.css"
    test_file.write_text("body { color: red; }")
    static_dir_str = str(static_dir)  # Flask requires str for static_folder

    app = flask.Flask(__name__, static_folder=static_dir_str)
    with app.test_request_context():
        # キャッシュバスティングあり
        url = pytilpack.flask.static_url_for("test.css")
        assert url.startswith("/static/test.css?v=")
        mtime = int(test_file.stat().st_mtime)
        assert f"v={mtime}" in url

        # キャッシュバスティングなし
        url = pytilpack.flask.static_url_for("test.css", cache_busting=False)
        assert url == "/static/test.css"

        # 存在しないファイル
        url = pytilpack.flask.static_url_for("notexist.css")
        assert url == "/static/notexist.css"


def test_run() -> None:
    """runのテスト。"""
    app = flask.Flask(__name__)

    @app.route("/hello")
    def index():
        return "Hello, World!"

    with pytilpack.flask.run(app):
        response = httpx.get("http://localhost:5000/hello")
        assert response.read() == b"Hello, World!"
        assert response.status_code == 200
