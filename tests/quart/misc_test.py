"""Quart miscのテスト。"""

import pathlib

import httpx
import pytest
import quart

import pytilpack.quart
import pytilpack.quart.misc


@pytest.mark.asyncio
async def test_run_sync():
    """run_syncのテスト。"""

    @pytilpack.quart.run_sync
    def sync_function(x: int, y: int) -> int:
        """同期関数の例。"""
        return x + y

    # 非同期関数として実行
    result = await sync_function(3, 5)
    assert result == 8

    # キーワード引数でもテスト
    result = await sync_function(x=10, y=20)
    assert result == 30


@pytest.mark.asyncio
async def test_static_url_for(tmp_path):
    """static_url_forのテスト。"""
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    test_file = static_dir / "test.css"
    test_file.write_text("body { color: red; }")
    static_dir_str = str(static_dir)  # Quart requires str for static_folder

    app = quart.Quart(__name__, static_folder=static_dir_str)
    async with app.test_request_context("/"):
        # キャッシュバスティングあり
        url = pytilpack.quart.static_url_for("test.css")
        assert url.startswith("/static/test.css?v=")
        mtime = int(test_file.stat().st_mtime)
        assert f"v={mtime}" in url

        # キャッシュバスティングなし
        url = pytilpack.quart.static_url_for("test.css", cache_busting=False)
        assert url == "/static/test.css"

        # 存在しないファイル
        url = pytilpack.quart.static_url_for("notexist.css")
        assert url == "/static/notexist.css"


@pytest.mark.asyncio
async def test_run(tmp_path: pathlib.Path) -> None:
    """runのテスト。"""
    (tmp_path / "hello.html").write_text("<p>Hello, {{ name }}!</p>\n")

    app = quart.Quart(__name__, template_folder=str(tmp_path))

    @app.route("/hello")
    def index():
        return "Hello, World!"

    async with pytilpack.quart.run(app):
        response = httpx.get("http://localhost:5000/hello")
        assert response.read() == b"Hello, World!"
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_routes() -> None:
    """get_routesのテスト。"""
    app = quart.Quart(__name__)

    @app.route("/")
    async def index():
        return "Home"

    @app.route("/users")
    async def users_list():
        return "Users"

    @app.route("/users/<int:user_id>")
    async def user_detail(user_id: int):
        return f"User {user_id}"

    @app.route("/users/<int:user_id>/posts/<post_id>")
    async def user_post(user_id: int, post_id: str):
        return f"User {user_id} Post {post_id}"

    @app.route("/api/v1/items/<item_id>")
    async def api_item(item_id: str):
        return f"Item {item_id}"

    async with app.test_request_context("/"):
        routes = pytilpack.quart.misc.get_routes(app)

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


@pytest.mark.asyncio
async def test_get_routes_application_root() -> None:
    """APPLICATION_ROOTが設定されている場合のget_routesのテスト。"""
    app = quart.Quart(__name__)
    app.config["APPLICATION_ROOT"] = "/myapp"

    @app.route("/test")
    async def test_endpoint():
        return "Test"

    async with app.test_request_context("/"):
        routes = pytilpack.quart.misc.get_routes(app)
        route_dict = {r.endpoint: r for r in routes}

        test_endpoint_route = route_dict["test_endpoint"]
        assert test_endpoint_route.url_parts == ["/myapp/test"]
        assert test_endpoint_route.arg_names == []
