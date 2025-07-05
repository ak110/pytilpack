"""Flask関連のその他のユーティリティ。"""

import base64
import contextlib
import logging
import pathlib
import re
import threading
import typing
import warnings

import flask
import httpx
import werkzeug.serving

import pytilpack.secrets
import pytilpack.web

logger = logging.getLogger(__name__)

_TIMESTAMP_CACHE: dict[str, int] = {}
"""静的ファイルの最終更新日時をキャッシュするための辞書。プロセス単位でキャッシュされる。"""


def generate_secret_key(cache_path: str | pathlib.Path) -> bytes:
    """deprecated."""
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
    path = flask.request.script_root + flask.request.path
    query_string = flask.request.query_string.decode("utf-8")
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
        return flask.url_for("static", filename=filename, **kwargs)

    # スタティックファイルのパスを取得
    static_folder = flask.current_app.static_folder
    assert static_folder is not None, "static_folder is None"

    filepath = pathlib.Path(static_folder) / filename
    try:
        # ファイルの最終更新日時のキャッシュを利用するか否か
        if cache_timestamp is True or (cache_timestamp == "when_not_debug" and not flask.current_app.debug):
            # キャッシュを使う
            timestamp = _TIMESTAMP_CACHE.get(str(filepath))
            if timestamp is None:
                timestamp = int(filepath.stat().st_mtime)
                _TIMESTAMP_CACHE[str(filepath)] = timestamp
        else:
            # キャッシュを使わない
            timestamp = int(filepath.stat().st_mtime)

        # キャッシュバスティングありのURLを返す
        return flask.url_for("static", filename=filename, v=timestamp, **kwargs)
    except OSError:
        # ファイルが存在しない場合などは通常のURLを返す
        return flask.url_for("static", filename=filename, **kwargs)


def get_safe_url(target: str | None, host_url: str, default_url: str) -> str:
    """deprecated."""
    warnings.warn(
        "pytilpack.flask_.get_safe_url is deprecated. Use pytilpack.web.get_safe_url instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return pytilpack.web.get_safe_url(target, host_url, default_url)


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


def get_routes(app: flask.Flask) -> list[RouteInfo]:
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
