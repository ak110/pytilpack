"""Flask miscのテスト。"""

import pathlib

import flask
import httpx

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

    with pytilpack.flask.run(app):
        response = httpx.get("http://localhost:5000/hello")
        assert response.read() == b"Hello, World!"
        assert response.status_code == 200


def test_get_routes() -> None:
    """get_routesのテスト。"""
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
