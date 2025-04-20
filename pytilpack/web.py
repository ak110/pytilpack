"""Web関係の一般的な処理をまとめたモジュール。"""

import logging
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
