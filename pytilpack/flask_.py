"""Flask関連のユーティリティ。"""

import base64
import contextlib
import logging
import pathlib
import secrets
import threading
import typing
import urllib.parse

import flask
import httpx
import werkzeug.serving
import werkzeug.test

logger = logging.getLogger(__name__)


def generate_secret_key(cache_path: str | pathlib.Path) -> bytes:
    """シークレットキーの作成/取得。

    既にcache_pathに保存済みならそれを返し、でなくば作成する。

    """
    cache_path = pathlib.Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("a+b") as secret:
        secret.seek(0)
        secret_key = secret.read()
        if not secret_key:
            secret_key = secrets.token_bytes()
            secret.write(secret_key)
            secret.flush()
        return secret_key


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


def get_safe_url(target: str, host_url: str, default_url: str) -> str:
    """ログイン時のリダイレクトとして安全なURLを返す。"""
    if target is None or target == "":
        return default_url
    ref_url = urllib.parse.urlparse(host_url)
    test_url = urllib.parse.urlparse(urllib.parse.urljoin(host_url, target))
    if test_url.scheme not in ("http", "https") or ref_url.netloc != test_url.netloc:
        logger.warning(f"Invalid next url: {target}")
        return default_url
    return target


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


def assert_bytes(response, status_code: int = 200) -> bytes:
    """flaskのテストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスボディ

    """
    response_body = response.get_data()

    if response.status_code != status_code:
        # エラーをraise
        assert (
            response.status_code == status_code
        ), f"ステータスコードエラー: {response.status_code} != {status_code}\n\n{response_body}"

    return response_body


def assert_html(response, status_code: int = 200) -> str:
    """flaskのテストコード用。

    html5libが必要なので注意。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスボディ (bs4.BeautifulSoup)

    """
    import html5lib

    response_body = response.get_data().decode("utf-8")

    # HTMLのチェック
    parser = html5lib.HTMLParser(strict=True)
    try:
        _ = parser.parse(response.data)
    except html5lib.html5parser.ParseError as e:
        raise AssertionError(f"HTMLエラー: {e}\n\n{response_body}") from e

    if response.status_code != status_code:
        # エラーをraise
        assert (
            response.status_code == status_code
        ), f"ステータスコードエラー: {response.status_code} != {status_code}\n\n{response_body}"

    return response_body


def assert_json(response, status_code: int = 200) -> dict[str, typing.Any]:
    """flaskのテストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスのjson

    """
    response_body = response.get_data().decode("utf-8")

    if response.status_code != status_code:
        # エラーをraise
        assert (
            response.status_code == status_code
        ), f"ステータスコードエラー: {response.status_code} != {status_code}\n\n{response_body}"

    return response.json
