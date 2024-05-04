"""Flask関連のユーティリティ。"""

import base64
import logging
import pathlib
import secrets
import urllib.parse

import flask

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
