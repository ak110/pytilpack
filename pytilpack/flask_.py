"""Flask関連のユーティリティ。"""

import base64
import contextlib
import json
import logging
import pathlib
import threading
import typing
import warnings
import xml.etree.ElementTree

import flask
import httpx
import werkzeug.middleware.proxy_fix
import werkzeug.serving

import pytilpack.pytest_
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


def assert_bytes(
    response,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = None,
) -> bytes:
    """flaskのテストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスボディ

    """
    response_body = response.get_data()

    try:
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        pytilpack.web.check_content_type(response.content_type, content_type)
    except AssertionError as e:
        logger.info(f"{e}\n\n{response_body!r}")
        raise e

    return response_body


def assert_html(
    response,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "__default__",
    tmp_path: pathlib.Path | None = None,
) -> str:
    """flaskのテストコード用。

    html5libが必要なので注意。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type
        tmp_path: 一時ファイルを保存するディレクトリ

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスボディ (bs4.BeautifulSoup)

    """
    import html5lib

    response_body = response.get_data().decode("utf-8")

    try:
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        if content_type == "__default__":
            content_type = ["text/html", "application/xhtml+xml"]
        pytilpack.web.check_content_type(response.content_type, content_type)

        # HTMLのチェック
        parser = html5lib.HTMLParser(strict=True, debug=True)
        try:
            _ = parser.parse(response.get_data())
        except html5lib.html5parser.ParseError as e:
            raise AssertionError(f"HTMLエラー: {e}") from e
    except AssertionError as e:
        tmp_file_path = pytilpack.pytest_.create_temp_view(
            tmp_path, response_body, ".html"
        )
        raise AssertionError(f"{e} (HTML: {tmp_file_path} )") from e

    return response_body


def assert_json(
    response,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "application/json",
) -> dict[str, typing.Any]:
    """flaskのテストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスのjson

    """
    response_body = response.get_data().decode("utf-8")

    try:
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        pytilpack.web.check_content_type(response.content_type, content_type)

        # JSONのチェック
        try:
            data = json.loads(response_body)
        except Exception as e:
            raise AssertionError(f"JSONエラー: {e}") from e
    except AssertionError as e:
        logger.info(f"{e}\n\n{response_body!r}")
        raise e

    return data


def assert_xml(
    response,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "__default__",
) -> str:
    """flaskのテストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスのxml

    """
    response_body = response.get_data().decode("utf-8")

    try:
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        if content_type == "__default__":
            content_type = ["text/xml", "application/xml"]
        pytilpack.web.check_content_type(response.content_type, content_type)

        # XMLのチェック
        try:
            _ = xml.etree.ElementTree.fromstring(response_body)
        except Exception as e:
            raise AssertionError(f"XMLエラー: {e}") from e
    except AssertionError as e:
        logger.info(f"{e}\n\n{response_body!r}")
        raise e

    return response_body


def check_status_code(status_code: int, valid_status_code: int) -> None:
    """deprecated."""
    warnings.warn(
        "pytilpack.flask_.check_status_code is deprecated. Use pytilpack.web.check_status_code instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    pytilpack.web.check_status_code(status_code, valid_status_code)


def check_content_type(
    content_type: str, valid_content_types: str | typing.Iterable[str] | None
) -> None:
    """deprecated."""
    warnings.warn(
        "pytilpack.flask_.check_content_type is deprecated. Use pytilpack.web.check_content_type instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    pytilpack.web.check_content_type(content_type, valid_content_types)


class ProxyFix(werkzeug.middleware.proxy_fix.ProxyFix):
    """リバースプロキシ対応。

    nginx.conf設定例::
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Forwarded-Prefix $http_x_forwarded_prefix;

    """

    def __init__(
        self,
        flaskapp: flask.Flask,
        x_for: int = 1,
        x_proto: int = 1,
        x_host: int = 0,
        x_port: int = 0,
        x_prefix: int = 1,
    ):
        super().__init__(
            flaskapp.wsgi_app,
            x_for=x_for,
            x_proto=x_proto,
            x_host=x_host,
            x_port=x_port,
            x_prefix=x_prefix,
        )
        self.flaskapp = flaskapp

    def __call__(self, environ, start_response):
        if self.x_prefix != 0:
            prefix = environ.get("HTTP_X_FORWARDED_PREFIX", "/")
            if prefix != "/":
                self.flaskapp.config["APPLICATION_ROOT"] = prefix
                self.flaskapp.config["SESSION_COOKIE_PATH"] = prefix
                self.flaskapp.config["REMEMBER_COOKIE_PATH"] = prefix
                environ["SCRIPT_NAME"] = prefix
                environ["PATH_INFO"] = environ["PATH_INFO"][len(prefix) :]
        return super().__call__(environ, start_response)
