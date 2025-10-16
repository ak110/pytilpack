"""Quart関連のその他のユーティリティ。"""

import asyncio
import contextlib
import functools
import logging
import pathlib
import re
import threading
import typing

import httpx
import quart
import quart.utils
import uvicorn

logger = logging.getLogger(__name__)

_TIMESTAMP_CACHE: dict[str, int] = {}
"""静的ファイルの最終更新日時をキャッシュするための辞書。プロセス単位でキャッシュされる。"""


def set_max_concurrency(app: quart.Quart, max_concurrency: int, timeout: float | None = 3.0) -> None:
    """
    Quart アプリ全体の最大同時リクエスト数を制限する。

    Args:
        app: 対象の Quart アプリケーション。
        max_concurrency: 許可する同時リクエスト数の上限。
        timeout: 最大待機秒数。タイムアウト時は 503 Service Unavailable を返す。

    Notes:
        * Hypercorn の ``--workers`` / ``--threads`` とは独立した
        アプリレベルの制御。1 ワーカー内のコルーチン数を絞る用途で使う。
    """

    if max_concurrency < 1:
        raise ValueError("max_concurrency must be >= 1")

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _acquire() -> None:  # before_request
        try:
            if timeout is None:
                await semaphore.acquire()
            else:
                await asyncio.wait_for(semaphore.acquire(), timeout=timeout)
            quart.g.quart__concurrency_token = True
        except TimeoutError:
            logger.warning(f"Concurrency limit reached, aborting request: {quart.request.path}")
            quart.abort(
                503,
                description="サーバーが混みあっています。しばらく待ってから再度お試しください。",
            )

    async def _release(_: typing.Any) -> None:
        if hasattr(quart.g, "quart__concurrency_token"):
            semaphore.release()
            del quart.g.quart__concurrency_token

    app.before_request(_acquire)
    app.teardown_request(_release)


def run_sync[**P, R](
    func: typing.Callable[P, R],
) -> typing.Callable[P, typing.Awaitable[R]]:
    """同期関数を非同期に実行するデコレーター。

    quart.utils.run_syncの型ヒントがいまいちなので用意。

    """

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        result = await quart.utils.run_sync(func)(*args, **kwargs)
        return typing.cast(R, result)

    return wrapper


def get_next_url() -> str:
    """ログイン後遷移用のnextパラメータ用のURLを返す。"""
    path = quart.request.script_root + quart.request.path
    query_string = quart.request.query_string.decode("utf-8")
    next_ = f"{path}?{query_string}" if query_string else path
    return next_


def static_url_for(
    filename: str,
    cache_busting: bool = True,
    cache_timestamp: bool | typing.Literal["when_not_debug"] = "when_not_debug",
    **kwargs,
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
        return quart.url_for("static", filename=filename, **kwargs)

    # スタティックファイルのパスを取得
    static_folder = quart.current_app.static_folder
    assert static_folder is not None, "static_folder is None"

    filepath = pathlib.Path(static_folder) / filename
    try:
        # ファイルの最終更新日時のキャッシュを利用するか否か
        if cache_timestamp is True or (cache_timestamp == "when_not_debug" and not quart.current_app.debug):
            # キャッシュを使う
            timestamp = _TIMESTAMP_CACHE.get(str(filepath))
            if timestamp is None:
                timestamp = int(filepath.stat().st_mtime)
                _TIMESTAMP_CACHE[str(filepath)] = timestamp
        else:
            # キャッシュを使わない
            timestamp = int(filepath.stat().st_mtime)

        # キャッシュバスティングありのURLを返す
        return quart.url_for("static", filename=filename, v=timestamp, **kwargs)
    except OSError:
        # ファイルが存在しない場合などは通常のURLを返す
        return quart.url_for("static", filename=filename, **kwargs)


class RouteInfo(typing.NamedTuple):
    """ルーティング情報を保持するクラス。

    Attributes:
        endpoint: エンドポイント名
        url_parts: URLのパーツのリスト
        arg_names: URLパーツの引数名のリスト
    """

    endpoint: str
    url_parts: list[str]
    arg_names: list[str]


def get_routes(app: quart.Quart) -> list[RouteInfo]:
    """ルーティング情報を取得する。

    Returns:
        ルーティング情報のリスト。
    """
    arg_regex = re.compile(r"<([^>]+)>")  # <name> <type:name> にマッチするための正規表現
    split_regex = re.compile(r"<[^>]+>")  # re.splitのためグループ無しにした版
    output: list[RouteInfo] = []
    for r in app.url_map.iter_rules():
        endpoint = str(r.endpoint)
        rule = (
            r.rule
            if app.config["APPLICATION_ROOT"] == "/" or not app.config["APPLICATION_ROOT"]
            else f"{app.config['APPLICATION_ROOT']}{r.rule}"
        )
        url_parts = [str(part) for part in split_regex.split(rule)]
        arg_names = [str(x.split(":")[-1]) for x in arg_regex.findall(rule)]
        output.append(RouteInfo(endpoint, url_parts, arg_names))
    return sorted(output, key=lambda x: len(x[2]), reverse=True)


@contextlib.asynccontextmanager
async def run(app: quart.Quart, host: str = "localhost", port: int = 5000):
    """Quartアプリを実行するコンテキストマネージャ。テストコードなど用。"""

    # ダミーエンドポイントが存在しない場合は追加
    if not any(rule.endpoint == "_pytilpack_quart_dummy" for rule in app.url_map.iter_rules()):

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
                    response = await client.get(f"http://{host}:{port}/_pytilpack_quart_dummy")
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
