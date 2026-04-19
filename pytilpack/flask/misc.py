"""Flask関連のその他のユーティリティ。"""

import base64
import contextlib
import logging
import pathlib
import threading
import typing
import warnings

import flask
import httpx
import werkzeug.serving

import pytilpack.secrets
import pytilpack.web

__all__ = [
    "generate_secret_key",
    "data_url",
    "get_next_url",
    "prefer_markdown",
    "static_url_for",
    "get_safe_url",
    "RouteInfo",
    "get_routes",
    "run",
]

logger = logging.getLogger(__name__)

_TIMESTAMP_CACHE: dict[str, int] = {}
"""静的ファイルの最終更新日時をキャッシュするための辞書。プロセス単位でキャッシュされる。"""


def generate_secret_key(cache_path: str | pathlib.Path) -> bytes:
    """Deprecated."""
    warnings.warn(
        "pytilpack.flask_.generate_secret_key is deprecated. Use pytilpack.secrets_.generate_secret_key instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return pytilpack.secrets.generate_secret_key(cache_path)


def data_url(data: bytes, mime_type: str) -> str:
    """小さい画像などのバイナリデータをURLに埋め込んだものを作って返す。

    Args:
        data: 埋め込むデータ
        mime_type: 例：'image/png'

    """
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{b64}"


def get_next_url() -> str:
    """ログイン後遷移用のnextパラメータ用のURLを返す。"""
    return pytilpack.web.build_next_url(
        flask.request.script_root,
        flask.request.path,
        flask.request.query_string.decode("utf-8"),
    )


def prefer_markdown() -> bool:
    """AcceptヘッダーでmarkdownがHTMLより優先されているかを返す。

    参考: <https://vercel.com/blog/making-agent-friendly-pages-with-content-negotiation>

    (CDNやプロキシがAcceptヘッダーを書き換える場合があるという話もあるが…。)

    Returns:
        markdownがHTMLより優先されている場合True、そうでなければFalse

    """
    return pytilpack.web.is_prefer_markdown(flask.request.headers.get("Accept", ""))


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
        **kwargs: flask.url_forに渡す追加の引数

    Returns:
        静的ファイルのURL
    """
    return pytilpack.web.resolve_static_url(
        flask.current_app.static_folder,
        filename,
        bool(flask.current_app.debug),
        cache_busting,
        cache_timestamp,
        lambda **kw: flask.url_for("static", **kw),
        _TIMESTAMP_CACHE,
        **kwargs,
    )


def get_safe_url(target: str | None, host_url: str, default_url: str) -> str:
    """Deprecated."""
    warnings.warn(
        "pytilpack.flask_.get_safe_url is deprecated. Use pytilpack.web.get_safe_url instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return pytilpack.web.get_safe_url(target, host_url, default_url)


# RouteInfoはpytilpack.webに集約。既存呼び出しのためflask名前空間にも公開する。
RouteInfo = pytilpack.web.RouteInfo


def get_routes(app: flask.Flask) -> list[RouteInfo]:
    """ルーティング情報を取得する。

    Returns:
        ルーティング情報のリスト。
    """
    return pytilpack.web.build_routes(app.url_map.iter_rules(), app.config.get("APPLICATION_ROOT"))


@contextlib.contextmanager
def run(app: flask.Flask, host: str = "localhost", port: int = 5000):
    """Flaskアプリを実行するコンテキストマネージャ。テストコードなど用。"""
    if not any(m.endpoint == "_pytilpack_flask_dummy" for m in app.url_map.iter_rules()):

        @app.route("/_pytilpack_flask_dummy")
        def _pytilpack_flask_dummy():
            return "OK"

    server = werkzeug.serving.make_server(host, port, app, threaded=True)
    ctx = app.app_context()
    ctx.push()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        # サーバーが起動するまで待機
        while True:
            try:
                httpx.get(f"http://{host}:{port}/_pytilpack_flask_dummy").raise_for_status()
                break
            except Exception:
                pass
        # 制御を戻す
        yield
    finally:
        server.shutdown()
        thread.join()
