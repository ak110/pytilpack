"""HTTP関連。"""

import collections.abc
import datetime
import email.utils
import logging
import re
import typing

logger = logging.getLogger(__name__)


def select_accept(accept_header: str, candidates: collections.abc.Sequence[str]) -> str | None:
    """Acceptヘッダーに基づいて候補MIMEタイプからベストマッチを返す。

    specificity・quality値を考慮して最適な候補を選択する。
    全候補が品質値0（拒否）の場合はNoneを返す。

    Acceptヘッダーが空の場合はRFC 7231に従い「何でも受け入れる」として扱い、
    candidatesの先頭を返す。

    内部でwerkzeugを使用するため、werkzeugのインストールが必要。

    Args:
        accept_header: Acceptヘッダーの値（生文字列）
        candidates: 候補MIMEタイプのリスト（サーバー側の優先順）

    Returns:
        最も優先されるMIMEタイプ。マッチするものがなければNone。

    """
    if not candidates:
        return None
    # Acceptヘッダーが空 = 何でも受け入れる → サーバー優先順で先頭を返す
    if not accept_header:
        return candidates[0]
    accept = _parse_mime_accept(accept_header)
    return accept.best_match(candidates)


def _parse_mime_accept(accept_header: str) -> typing.Any:
    """Acceptヘッダー文字列をwerkzeugのMIMEAcceptオブジェクトに変換する。"""
    try:
        import werkzeug.datastructures
        import werkzeug.http
    except ImportError:
        raise ImportError(
            "werkzeugが必要です。pip install pytilpack[flask] または pip install pytilpack[quart] でインストールしてください。"
        ) from None
    return werkzeug.http.parse_accept_header(accept_header, werkzeug.datastructures.MIMEAccept)


def get_status_code_from_exception(exc: Exception) -> int | None:
    """例外からステータスコードを取得する。

    少なくともrequestsとhttpxのraise_for_status()で発生する例外に対応している。
    """
    if (
        (
            hasattr(exc, "response")
            and (response := exc.response) is not None  # pyright: ignore[reportAttributeAccessIssue]
            and hasattr(response, "status_code")
            and (status_code := response.status_code) is not None  # pyright: ignore[reportAttributeAccessIssue]
        )
        or hasattr(exc, "status_code")
        and (status_code := exc.status_code) is not None  # pyright: ignore[reportAttributeAccessIssue]
    ):
        status_code = str(status_code)
        if status_code.isdigit():
            int_status_code = int(status_code)
            if 100 <= int_status_code <= 599:
                return int_status_code
    return None


def get_retry_after_from_exception(exc: Exception) -> float | None:
    """例外から Retry-After ヘッダーを取得して解析する。

    少なくともrequestsとhttpxのraise_for_status()で発生する例外に対応している。
    """
    if (
        hasattr(exc, "response")
        and (response := exc.response) is not None  # pyright: ignore[reportAttributeAccessIssue]
        and hasattr(response, "headers")
        and (headers := response.headers) is not None  # pyright: ignore[reportAttributeAccessIssue]
    ):
        retry_after_header = headers.get("Retry-After")
        logger.info(f"Retry-After: {retry_after_header}")
        return get_retry_after(retry_after_header)
    return None


def get_retry_after(retry_after_header: str | None) -> float | None:
    """Retry-After ヘッダーを解析して、待機すべき秒数を返す。"""
    if not retry_after_header:
        return None
    # 整数秒形式
    # Retry-After: <delay-seconds> レスポンスを受信してから遅延する秒数を示す負でない 10 進数の整数。
    # 独自拡張として一応小数も許容する
    if re.fullmatch(r"\d+(\.\d+)?", retry_after_header):
        return float(retry_after_header)
    # 日時形式
    # Retry-After: <http-date> 再試行する日付
    try:
        dt = email.utils.parsedate_to_datetime(retry_after_header)
        # parsedate_to_datetime はタイムゾーン情報付き（あるいは naive）を返す
        # dt が naive なら UTC とみなす
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.UTC)
        # 現在の UTC 時刻を aware で取得
        now = datetime.datetime.now(tz=datetime.UTC)
        delta = (dt - now).total_seconds()
        return max(delta, 0.0)
    except Exception:
        return None
