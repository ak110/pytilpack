"""Quart関連のその他のユーティリティ。"""

import asyncio
import contextlib
import pathlib
import threading
import typing

import httpx
import quart
import uvicorn

_TIMESTAMP_CACHE: dict[str, int] = {}
"""静的ファイルの最終更新日時をキャッシュするための辞書。プロセス単位でキャッシュされる。"""


def static_url_for(
    filename: str,
    cache_busting: bool = True,
    cache_timestamp: bool | typing.Literal["when_not_debug"] = "when_not_debug",
) -> str:
    """静的ファイルのURLを生成します。

    Args:
        filename: 静的ファイルの名前
        cache_busting: キャッシュバスティングを有効にするかどうか (デフォルト: True)
        cache_timestamp: キャッシュバスティングするときのファイルの最終更新日時をプロセス単位でキャッシュするか否か。
            - True: プロセス単位でキャッシュする。プロセスの再起動やSIGHUPなどをしない限り更新されない。
            - False: キャッシュしない。常に最新を参照する。
            - "when_not_debug": デバッグモードでないときのみキャッシュする。

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
        # ファイルの最終更新日時のキャッシュを利用するか否か
        if cache_timestamp is True or (
            cache_timestamp == "when_not_debug" and not quart.current_app.debug
        ):
            # キャッシュを使う
            timestamp = _TIMESTAMP_CACHE.get(str(filepath))
            if timestamp is None:
                timestamp = int(filepath.stat().st_mtime)
                _TIMESTAMP_CACHE[str(filepath)] = timestamp
        else:
            # キャッシュを使わない
            timestamp = int(filepath.stat().st_mtime)

        # キャッシュバスティングありのURLを返す
        return quart.url_for("static", filename=filename, v=timestamp)
    except OSError:
        # ファイルが存在しない場合などは通常のURLを返す
        return quart.url_for("static", filename=filename)


@contextlib.asynccontextmanager
async def run(app: quart.Quart, host: str = "localhost", port: int = 5000):
    """Quartアプリを実行するコンテキストマネージャ。テストコードなど用。"""

    # ダミーエンドポイントが存在しない場合は追加
    if not any(
        rule.endpoint == "_pytilpack_quart_dummy" for rule in app.url_map.iter_rules()
    ):

        @app.route("/_pytilpack_quart_dummy")
        async def _pytilpack_quart_dummy():
            return "OK"

    # Uvicornサーバーの設定
    config = uvicorn.Config(app=app, host=host, port=port)
    server = uvicorn.Server(config)

    # 別スレッドでサーバーを起動
    def run_server():
        asyncio.run(server.serve())

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    try:
        # サーバーが起動するまで待機
        async with httpx.AsyncClient() as client:
            while True:
                try:
                    response = await client.get(
                        f"http://{host}:{port}/_pytilpack_quart_dummy"
                    )
                    response.raise_for_status()
                    break
                except Exception:
                    await asyncio.sleep(0.1)  # 少し待機

        # 制御を戻す
        yield

    finally:
        # サーバーを停止
        server.should_exit = True
        thread.join(timeout=5.0)  # タイムアウトを設定
