"""Quart関連のその他のユーティリティ。"""

import asyncio
import contextlib
import dataclasses
import functools
import logging
import threading
import typing

import httpx
import quart
import quart.utils
import uvicorn

import pytilpack.web

__all__ = [
    "ConcurrencyState",
    "set_max_concurrency",
    "exhaust_concurrency",
    "run_sync",
    "get_next_url",
    "prefer_markdown",
    "static_url_for",
    "RouteInfo",
    "get_routes",
    "run",
]

logger = logging.getLogger(__name__)

_TIMESTAMP_CACHE: dict[str, int] = {}
"""静的ファイルの最終更新日時をキャッシュするための辞書。プロセス単位でキャッシュされる。"""


@dataclasses.dataclass
class ConcurrencyState:
    """set_max_concurrency の内部状態。exhaust_concurrency から参照される。"""

    semaphore: asyncio.Semaphore
    max_concurrency: int
    timeout: float | None


def set_max_concurrency(app: quart.Quart, max_concurrency: int, timeout: float | None = 3.0) -> None:
    """Quart アプリ全体の最大同時リクエスト数を制限する。

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
    state = ConcurrencyState(
        semaphore=semaphore,
        max_concurrency=max_concurrency,
        timeout=timeout,
    )
    app.extensions["pytilpack_concurrency"] = state

    async def _acquire() -> None:  # before_request
        try:
            # テスト時にセマフォ/timeoutを一時変更できるようstateから読む
            sem = state.semaphore
            to = state.timeout
            if to is None:
                await sem.acquire()
            else:
                await asyncio.wait_for(sem.acquire(), timeout=to)
            quart.g.quart__concurrency_token = True
        except TimeoutError:
            logger.warning(f"Concurrency limit reached, aborting request: {quart.request.path}")
            quart.abort(
                503,
                description="サーバーが混みあっています。しばらく待ってから再度お試しください。",
            )

    async def _release(_: typing.Any) -> None:
        if hasattr(quart.g, "quart__concurrency_token"):
            state.semaphore.release()
            del quart.g.quart__concurrency_token

    app.before_request(_acquire)
    app.teardown_request(_release)


@contextlib.asynccontextmanager
async def exhaust_concurrency(app: quart.Quart):
    """テスト用: セマフォを枯渇させて503を発生させるコンテキストマネージャ。

    使用例::

        async with pytilpack.quart.exhaust_concurrency(app):
            response = await client.get("/any-endpoint")
            assert response.status_code == 503
    """
    state: ConcurrencyState = app.extensions["pytilpack_concurrency"]
    original_semaphore = state.semaphore
    original_timeout = state.timeout

    # スロット0のセマフォに差し替えて即座にタイムアウト→503を返すようにする
    state.semaphore = asyncio.Semaphore(0)
    state.timeout = 0.01

    try:
        yield
    finally:
        state.semaphore = original_semaphore
        state.timeout = original_timeout


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
    return pytilpack.web.build_next_url(
        quart.request.script_root,
        quart.request.path,
        quart.request.query_string.decode("utf-8"),
    )


def prefer_markdown() -> bool:
    """AcceptヘッダーでmarkdownがHTMLより優先されているかを返す。

    参考: <https://vercel.com/blog/making-agent-friendly-pages-with-content-negotiation>

    (CDNやプロキシがAcceptヘッダーを書き換える場合があるという話もあるが…。)

    Returns:
        markdownがHTMLより優先されている場合True、そうでなければFalse

    """
    return pytilpack.web.is_prefer_markdown(quart.request.headers.get("Accept", ""))


def static_url_for(
    filename: str,
    cache_busting: bool = True,
    cache_timestamp: bool | typing.Literal["when_not_debug"] = "when_not_debug",
    **kwargs: typing.Any,
) -> str:
    """静的ファイルのURLを生成する。

    Args:
        filename: 静的ファイルの名前
        cache_busting: キャッシュバスティングを有効にするかどうか (デフォルト: True)
        cache_timestamp: キャッシュバスティングするときのファイルの最終更新日時をプロセス単位でキャッシュするか否か。
            - True: プロセス単位でキャッシュする。プロセスの再起動やSIGHUPなどをしない限り更新されない。
            - False: キャッシュしない。常に最新を参照する。
            - "when_not_debug": デバッグモードでないときのみキャッシュする。
        **kwargs: その他の引数 (quart.url_forに渡される)

    Returns:
        静的ファイルのURL
    """
    return pytilpack.web.resolve_static_url(
        quart.current_app.static_folder,
        filename,
        bool(quart.current_app.debug),
        cache_busting,
        cache_timestamp,
        lambda **kw: quart.url_for("static", **kw),
        _TIMESTAMP_CACHE,
        **kwargs,
    )


# RouteInfoはpytilpack.webに集約。既存呼び出しのためquart名前空間にも公開する。
RouteInfo = pytilpack.web.RouteInfo


def get_routes(app: quart.Quart) -> list[RouteInfo]:
    """ルーティング情報を取得する。

    Returns:
        ルーティング情報のリスト。
    """
    return pytilpack.web.build_routes(app.url_map.iter_rules(), app.config.get("APPLICATION_ROOT"))


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
