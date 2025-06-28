"""Web関係の一般的な処理をまとめたモジュール。"""

import logging
import typing
import urllib.parse

logger = logging.getLogger(__name__)


def get_safe_url(target: str | None, host_url: str, default_url: str) -> str:
    """ログイン時のリダイレクトとして安全なURLを返す。

    Args:
        target: リダイレクト先のURL
        host_url: ホストのURL
        default_url: デフォルトのURL

    Returns:
        安全なURL
    """
    if target is None or target == "":
        return default_url
    ref_url = urllib.parse.urlparse(host_url)
    test_url = urllib.parse.urlparse(urllib.parse.urljoin(host_url, target))
    if test_url.scheme not in ("http", "https") or ref_url.netloc != test_url.netloc:
        logger.warning(f"Invalid next url: {target}")
        return default_url
    return target


def check_status_code(status_code: int, valid_status_code: int) -> None:
    """ステータスコードのチェック。"""
    if status_code != valid_status_code:
        raise AssertionError(f"ステータスコードエラー: {status_code} != {valid_status_code}")


def check_content_type(content_type: str, valid_content_types: str | typing.Iterable[str] | None) -> None:
    """Content-Typeのチェック。"""
    if valid_content_types is None:
        return None
    if isinstance(valid_content_types, str):
        valid_content_types = [valid_content_types]
    if not any(content_type.startswith(c) for c in valid_content_types):
        raise AssertionError(f"Content-Typeエラー: {content_type} != {valid_content_types}")
    return None


def check_html(input_stream: typing.Any, strict: bool = False) -> None:
    """HTMLのチェック。html5libが必要なので注意。"""
    import html5lib
    import html5lib.constants

    parser = html5lib.HTMLParser(debug=True)
    _ = parser.parse(input_stream)
    if len(parser.errors) > 0:
        errors = [
            f"{position}: {html5lib.constants.E[errorcode] % datavars}" for position, errorcode, datavars in parser.errors
        ]
        if strict:
            error_str = "\n".join(errors)
            raise AssertionError(f"HTMLエラー: {error_str}")
        for error in errors:
            logger.warning(f"HTMLエラー: {error}")
