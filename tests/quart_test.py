"""Quartユーティリティのテスト。"""

import pytest
import quart

import pytilpack.quart_


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
        url = pytilpack.quart_.static_url_for("test.css")
        assert url.startswith("/static/test.css?v=")
        mtime = int(test_file.stat().st_mtime)
        assert f"v={mtime}" in url

        # キャッシュバスティングなし
        url = pytilpack.quart_.static_url_for("test.css", cache_busting=False)
        assert url == "/static/test.css"

        # 存在しないファイル
        url = pytilpack.quart_.static_url_for("notexist.css")
        assert url == "/static/notexist.css"
