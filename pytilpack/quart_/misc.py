"""Quart関連のその他のユーティリティ。"""

import pathlib

import quart


def static_url_for(filename: str, cache_busting: bool = True) -> str:
    """静的ファイルのURLを生成します。

    Args:
        filename: 静的ファイルの名前
        cache_busting: キャッシュバスティングを有効にするかどうか (デフォルト: True)

    Returns:
        静的ファイルのURL
    """
    if not cache_busting:
        return quart.url_for("static", filename=filename)

    # スタティックファイルのパスを取得
    static_folder = quart.current_app.static_folder
    assert static_folder is not None, "static_folder is None"

    filepath = pathlib.Path(static_folder) / filename
    try:
        # ファイルの最終更新時刻をキャッシュバスティングに使用
        timestamp = int(filepath.stat().st_mtime)
        return quart.url_for("static", filename=filename, v=timestamp)
    except OSError:
        # ファイルが存在しない場合は通常のURLを返す
        return quart.url_for("static", filename=filename)
