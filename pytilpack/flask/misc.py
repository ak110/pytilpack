__lazy_modules__ = [
    "contextlib",
    "flask",
    "httpx",
    "logging",
    "pathlib",
    "pytilpack.data_url",
    "pytilpack.python",
    "pytilpack.web",
    "threading",
    "time",
    "typing",
    "werkzeug.serving",
]

import contextlib
import logging
import pathlib
import threading
import time
import typing

import flask
import httpx
import werkzeug.serving

import pytilpack.data_url
import pytilpack.python
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


@pytilpack.python.deprecated("Use pytilpack.secrets.generate_secret_key instead.")
def generate_secret_key(cache_path: str | pathlib.Path) -> bytes:
    # secretsはUnix専用fcntlを使うため、この機能を呼ぶ場合だけ読み込む。
    import pytilpack.secrets  # pylint: disable=import-outside-toplevel,redefined-outer-name

    return pytilpack.secrets.generate_secret_key(cache_path)


def data_url(data: bytes, mime_type: str) -> str:
    return pytilpack.data_url.create(mime_type, data)


def get_next_url() -> str:
    return pytilpack.web.build_next_url(
        flask.request.script_root,
        flask.request.path,
        flask.request.query_string.decode("utf-8"),
    )


def prefer_markdown() -> bool:
    return pytilpack.web.is_prefer_markdown(flask.request.headers.get("Accept", ""))


def static_url_for(
    filename: str,
    cache_busting: bool = True,
    cache_timestamp: bool | typing.Literal["when_not_debug"] = "when_not_debug",
    **kwargs: typing.Any,
) -> str:
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


@pytilpack.python.deprecated("Use pytilpack.web.get_safe_url instead.")
def get_safe_url(target: str | None, host_url: str, default_url: str) -> str:
    return pytilpack.web.get_safe_url(target, host_url, default_url)


RouteInfo = pytilpack.web.RouteInfo


def get_routes(app: flask.Flask) -> list[RouteInfo]:
    return pytilpack.web.build_routes(app.url_map.iter_rules(), app.config.get("APPLICATION_ROOT"))


@contextlib.contextmanager
def run(app: flask.Flask, host: str = "localhost", port: int = 5000):
    if not any(m.endpoint == "_pytilpack_flask_dummy" for m in app.url_map.iter_rules()):

        @app.route("/_pytilpack_flask_dummy")
        def _pytilpack_flask_dummy():
            return "OK"

    with werkzeug.serving.make_server(host, port, app, threaded=True) as server, app.app_context():
        failures: list[BaseException] = []

        def serve():
            try:
                server.serve_forever()
            except BaseException as exc:
                failures.append(exc)

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10.0
            while True:
                if not thread.is_alive():
                    raise RuntimeError(
                        "Flaskサーバーの起動に失敗しました。原因は連鎖した例外を参照し、host・portの指定（使用中のポートなど）を見直す"
                    ) from (failures[0] if failures else None)
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        "Flaskサーバーの起動待ちが10秒を超えました。host・portへ接続できるか（ファイアウォール、名前解決）を確かめて再実行する"
                    )
                try:
                    httpx.get(f"http://{host}:{server.server_port}/_pytilpack_flask_dummy", timeout=0.2).raise_for_status()
                    break
                except httpx.HTTPError:
                    time.sleep(0.05)
            yield server.server_port
        finally:
            if thread.is_alive():
                server.shutdown()
            thread.join(timeout=5.0)
            if thread.is_alive():
                raise RuntimeError(
                    "Flaskサーバーの停止に失敗しました。サーバースレッドが5秒以内に終了せずdaemonスレッドとして残っている。"
                    "終了しないリクエスト処理が無いかを確かめる"
                )
