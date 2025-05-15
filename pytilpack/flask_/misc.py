"""Flask関連のその他のユーティリティ。"""

import base64
import contextlib
import logging
import pathlib
import threading
import warnings

import flask
import httpx
import werkzeug.serving

import pytilpack.secrets_
import pytilpack.web

logger = logging.getLogger(__name__)


def generate_secret_key(cache_path: str | pathlib.Path) -> bytes:
    """deprecated."""
    warnings.warn(
        "pytilpack.flask_.generate_secret_key is deprecated. Use pytilpack.secrets_.generate_secret_key instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return pytilpack.secrets_.generate_secret_key(cache_path)


def data_url(data: bytes, mime_type: str) -> str:
    """小さい画像などのバイナリデータをURLに埋め込んだものを作って返す。

    Args:
        data: 埋め込むデータ
        mime_type: 例：'image/png'

    """
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{b64}"


def get_next_url() -> str:
    """flask_loginのnextパラメータ用のURLを返す。"""
    path = flask.request.script_root + flask.request.path
    query_string = flask.request.query_string.decode("utf-8")
    next_ = f"{path}?{query_string}" if query_string else path
    return next_


def get_safe_url(target: str | None, host_url: str, default_url: str) -> str:
    """deprecated."""
    warnings.warn(
        "pytilpack.flask_.get_safe_url is deprecated. Use pytilpack.web.get_safe_url instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return pytilpack.web.get_safe_url(target, host_url, default_url)


@contextlib.contextmanager
def run(app: flask.Flask, host: str = "localhost", port: int = 5000):
    """Flaskアプリを実行するコンテキストマネージャ。テストコードなど用。"""

    if not any(
        m.endpoint == "_pytilpack_flask_dummy" for m in app.url_map.iter_rules()
    ):

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
                httpx.get(
                    f"http://{host}:{port}/_pytilpack_flask_dummy"
                ).raise_for_status()
                break
            except Exception:
                pass
        # 制御を戻す
        yield
    finally:
        server.shutdown()
        thread.join()
