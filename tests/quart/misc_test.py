"""Quart miscのテスト。"""

import httpx
import pytest
import quart

import pytilpack.quart


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
async def test_run():
    """runのテスト。"""
    app = quart.Quart(__name__)

    @app.route("/hello")
    def index():
        return "Hello, World!"

    async with pytilpack.quart.run(app):
        response = httpx.get("http://localhost:5000/hello")
        assert response.read() == b"Hello, World!"
        assert response.status_code == 200
