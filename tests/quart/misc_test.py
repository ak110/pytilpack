"""Quart miscのテスト。"""

import asyncio
import contextlib
import pathlib
import typing

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

    # tests/flask/misc_test.py::test_run が既定の5000を使うため、xdist並列実行時の
    # ポート衝突を避けるためQuart側は5004を使う。
    async with pytilpack.quart.run(app, port=5004):
        response = httpx.get("http://localhost:5004/hello")
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

        # pylint: disable=duplicate-code
        # Flask/Quartの並行実装を同一ルート定義で検証する定型アサーションのため許容する。
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


@pytest.mark.asyncio
async def test_set_max_concurrency() -> None:
    """set_max_concurrencyのテスト。"""
    # max_concurrency < 1 で ValueError
    with pytest.raises(ValueError):
        pytilpack.quart.set_max_concurrency(quart.Quart(__name__), 0)

    # 通常リクエストが通ること
    app = quart.Quart(__name__)

    @app.route("/test")
    async def test_endpoint():
        return "OK"

    pytilpack.quart.set_max_concurrency(app, 2, timeout=0.01)

    async with app.test_client() as client:
        assert (await client.get("/test")).status_code == 200

    # ConcurrencyStateがextensionsに保存されていること
    state = app.extensions["pytilpack_concurrency"]
    assert isinstance(state, pytilpack.quart.misc.ConcurrencyState)
    assert state.max_concurrency == 2
    assert state.timeout == 0.01


@pytest.mark.asyncio
async def test_set_max_concurrency_no_timeout() -> None:
    """set_max_concurrency(timeout=None)のテスト。"""
    app = quart.Quart(__name__)

    @app.route("/test")
    async def test_endpoint():
        return "OK"

    pytilpack.quart.set_max_concurrency(app, 1, timeout=None)

    async with app.test_client() as client:
        assert (await client.get("/test")).status_code == 200


@pytest.mark.asyncio
async def test_exhaust_concurrency() -> None:
    """exhaust_concurrencyのテスト。"""
    app = quart.Quart(__name__)

    @app.route("/test")
    async def test_endpoint():
        return "OK"

    pytilpack.quart.set_max_concurrency(app, 2, timeout=1.0)

    async with app.test_client() as client:
        # 通常は通る
        assert (await client.get("/test")).status_code == 200

        # exhaust中は503
        async with pytilpack.quart.exhaust_concurrency(app):
            assert (await client.get("/test")).status_code == 503

        # exhaust後は復帰
        assert (await client.get("/test")).status_code == 200


@pytest.mark.asyncio
async def test_set_max_concurrency_duplicate() -> None:
    """set_max_concurrencyを同一アプリに二度呼ぶとRuntimeErrorが送出されることのテスト。"""
    app = quart.Quart(__name__)
    pytilpack.quart.set_max_concurrency(app, 2)
    with pytest.raises(RuntimeError, match="already configured"):
        pytilpack.quart.set_max_concurrency(app, 1)


@pytest.mark.asyncio
async def test_set_max_concurrency_cancel_releases_semaphore() -> None:
    """キャンセル時にセマフォが解放されることのテスト。

    before_request に登録された _acquire を Quart のリクエストコンテキスト下で
    直接キャンセルし、セマフォが漏洩しないことを確認する。
    """
    app = quart.Quart(__name__)
    pytilpack.quart.set_max_concurrency(app, 1, timeout=None)
    state: pytilpack.quart.misc.ConcurrencyState = app.extensions["pytilpack_concurrency"]

    # set_max_concurrency が before_request に登録した _acquire を取り出す
    (acquire_func,) = app.before_request_funcs[None]

    async with app.test_request_context("/"):
        assert not state.semaphore.locked()  # 初期値（解放済み）

        # セマフォを枯渇させて _acquire が待機状態に入るよう準備する
        await state.semaphore.acquire()
        assert state.semaphore.locked()

        # _acquire をタスクとして起動（セマフォ待機に入る）。
        # before_request_funcs から取り出した関数の戻り値型はQuartの汎用型のため、
        # Coroutine[Any, Any, None] としてキャストして型検査を通す。
        task: asyncio.Task[None] = asyncio.create_task(
            typing.cast("typing.Coroutine[typing.Any, typing.Any, None]", acquire_func())
        )
        # イベントループに制御を渡して _acquire が待機状態へ移行するまで進める
        await asyncio.sleep(0)

        # タスクをキャンセルして CancelledError を発行する
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

        # 手動取得分を解放する
        state.semaphore.release()
        # セマフォが漏洩していなければ解放済みのまま（_acquire は未取得でキャンセル）
        assert not state.semaphore.locked()


@pytest.mark.asyncio
async def test_prefer_markdown() -> None:
    """prefer_markdownのテスト。"""
    app = quart.Quart(__name__)

    async with app.test_request_context(
        "/",
        headers={"Accept": "text/markdown;q=0.9, text/html;q=0.8, */*;q=0.7"},
    ):
        assert pytilpack.quart.prefer_markdown() is True

    async with app.test_request_context(
        "/",
        headers={"Accept": "text/html;q=0.9, */*;q=0.8"},
    ):
        assert pytilpack.quart.prefer_markdown() is False

    async with app.test_request_context(
        "/",
        headers={"Accept": "text/html;q=0.8, */*;q=0.8"},
    ):
        assert pytilpack.quart.prefer_markdown() is False

    async with app.test_request_context(
        "/",
        headers={"Accept": "text/plain;q=0.7, */*;q=0.6"},
    ):
        assert pytilpack.quart.prefer_markdown() is True
