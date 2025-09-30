"""HTTP関連。"""

import datetime
import email.utils
import logging
import re

logger = logging.getLogger(__name__)


def get_retry_after_from_exception(exc: Exception) -> float | None:
    """例外から Retry-After ヘッダーを取得して解析する。"""
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
