"""Flask miscのテスト。"""

import pathlib
import socket
import types

import flask
import httpx
import pytest

import pytilpack.flask
import pytilpack.flask.misc


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

    with pytilpack.flask.run(app, port=0) as port:
        assert port > 0
        response = httpx.get(f"http://localhost:{port}/hello", timeout=5)
        assert response.read() == b"Hello, World!"
        assert response.status_code == 200

    with socket.socket() as client:
        client.settimeout(0.2)
        assert client.connect_ex(("localhost", port)) != 0
    assert not flask.has_app_context()


def test_run_bind_failure() -> None:
    """使用中のポートを指定すると起動へ進まず有限時間で失敗する。"""
    app = flask.Flask(__name__)
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        with pytest.raises(SystemExit), pytilpack.flask.run(app, host="127.0.0.1", port=occupied.getsockname()[1]):
            pytest.fail("使用中のポートで起動した")
    assert not flask.has_app_context()


def test_run_startup_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """起動待ち上限に達するとサーバーとアプリコンテキストを回収する。"""
    ticks = iter((0.0, 11.0))
    monkeypatch.setattr(pytilpack.flask.misc, "time", types.SimpleNamespace(monotonic=lambda: next(ticks)))
    with pytest.raises(TimeoutError, match="10秒"), pytilpack.flask.run(flask.Flask(__name__), host="127.0.0.1", port=0):
        pytest.fail("上限を超えて起動した")
    assert not flask.has_app_context()


def test_get_routes() -> None:
    """get_routesのテスト。"""
    # arid: disable
    # Flask/Quartの並行実装を同一ルート定義で検証する定型アサーションのため許容する。
    app = flask.Flask(__name__)

    @app.route("/")
    def index():
        return "Home"

    @app.route("/users")
    def users_list():
        return "Users"

    @app.route("/users/<int:user_id>")
    def user_detail(user_id: int):
        return f"User {user_id}"

    @app.route("/users/<int:user_id>/posts/<post_id>")
    def user_post(user_id: int, post_id: str):
        return f"User {user_id} Post {post_id}"

    @app.route("/api/v1/items/<item_id>")
    def api_item(item_id: str):
        return f"Item {item_id}"

    with app.test_request_context():
        routes = pytilpack.flask.misc.get_routes(app)

        # 引数の多い順にソートされることを確認
        assert len(routes[0].arg_names) >= len(routes[-1].arg_names)

        # 各ルートの内容を確認
        route_dict = {r.endpoint: r for r in routes}

        # "/" ルート
        index_route = route_dict["index"]
        assert index_route.url_parts == ["/"]
        assert index_route.arg_names == []

        # "/users" ルート
        users_route = route_dict["users_list"]
        assert users_route.url_parts == ["/users"]
        assert users_route.arg_names == []

        # "/users/<int:user_id>" ルート
        user_detail_route = route_dict["user_detail"]
        assert user_detail_route.url_parts == ["/users/", ""]
        assert user_detail_route.arg_names == ["user_id"]

        # "/users/<int:user_id>/posts/<post_id>" ルート
        user_post_route = route_dict["user_post"]
        assert user_post_route.url_parts == ["/users/", "/posts/", ""]
        assert user_post_route.arg_names == ["user_id", "post_id"]

        # "/api/v1/items/<item_id>" ルート
        api_item_route = route_dict["api_item"]
        assert api_item_route.url_parts == ["/api/v1/items/", ""]
        assert api_item_route.arg_names == ["item_id"]
    # arid: enable


def test_get_routes_application_root() -> None:
    """APPLICATION_ROOTが設定されている場合のget_routesのテスト。"""
    app = flask.Flask(__name__)
    app.config["APPLICATION_ROOT"] = "/myapp"

    @app.route("/test")
    def test_endpoint():
        return "Test"

    with app.test_request_context():
        routes = pytilpack.flask.misc.get_routes(app)
        route_dict = {r.endpoint: r for r in routes}

        test_endpoint_route = route_dict["test_endpoint"]
        assert test_endpoint_route.url_parts == ["/myapp/test"]
        assert test_endpoint_route.arg_names == []


def test_prefer_markdown() -> None:
    """prefer_markdownのテスト。"""
    app = flask.Flask(__name__)

    with app.test_request_context(
        "/",
        headers={"Accept": "text/markdown;q=0.9, text/html;q=0.8, */*;q=0.7"},
    ):
        assert pytilpack.flask.prefer_markdown() is True

    with app.test_request_context(
        "/",
        headers={"Accept": "text/html;q=0.9, */*;q=0.8"},
    ):
        assert pytilpack.flask.prefer_markdown() is False

    with app.test_request_context(
        "/",
        headers={"Accept": "text/html;q=0.8, */*;q=0.8"},
    ):
        assert pytilpack.flask.prefer_markdown() is False

    with app.test_request_context(
        "/",
        headers={"Accept": "text/plain;q=0.7, */*;q=0.6"},
    ):
        assert pytilpack.flask.prefer_markdown() is True
