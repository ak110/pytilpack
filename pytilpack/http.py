"""HTTP関連。"""

__lazy_modules__ = [
    "collections.abc",
    "contextlib",
    "dataclasses",
    "datetime",
    "email.utils",
    "http",
    "json",
    "logging",
    "re",
    "sys",
    "typing",
    "urllib.parse",
    "werkzeug.datastructures",
    "werkzeug.http",
]

import collections.abc
import contextlib
import dataclasses
import datetime as dt
import email.utils
import http
import json
import logging
import re
import sys
import typing
import urllib.parse

import werkzeug.datastructures
import werkzeug.http

logger = logging.getLogger(__name__)

PROBLEM_JSON_CONTENT_TYPE = "application/problem+json"


def select_accept(accept_header: str, candidates: collections.abc.Sequence[str]) -> str | None:
    """Acceptヘッダーに基づいて候補MIMEタイプから優先度最上位の値を返す。

    specificity・quality値を考慮して選択する。
    全候補が品質値0（拒否）の場合はNoneを返す。

    Acceptヘッダーが空の場合はRFC 7231に従い「何でも受け入れる」として扱い、
    candidatesの先頭を返す。

    Args:
        accept_header: Acceptヘッダーの値（生文字列）
        candidates: 候補MIMEタイプのリスト（サーバー側の優先順）

    Returns:
        優先度最上位のMIMEタイプ。一致するものがなければNone。

    """
    if not candidates:
        return None
    # Acceptヘッダーが空 = 何でも受け入れる → サーバー優先順で先頭を返す
    if not accept_header:
        return candidates[0]
    accept = werkzeug.http.parse_accept_header(accept_header, werkzeug.datastructures.MIMEAccept)
    return accept.best_match(candidates)


def select_accept_language(
    header: str,
    supported: collections.abc.Sequence[str],
    default: str | None = None,
) -> str | None:
    """Accept-Languageヘッダーからサポート済みロケールの優先度最上位の値を返す。

    quality値を考慮して選択する。

    Args:
        header: Accept-Languageヘッダーの値（生文字列）
        supported: サポートするロケールのリスト（例: ["en", "ja", "ko"]）
        default: 一致するものがない場合のデフォルト値

    Returns:
        優先度最上位のロケール。一致するものがなければdefault。

    """
    if not supported:
        return default
    if not header:
        return default
    accept = werkzeug.http.parse_accept_header(header, werkzeug.datastructures.LanguageAccept)
    result = accept.best_match(supported)
    return result if result is not None else default


def make_problem_details(
    status: int,
    title: str | None = None,
    *,
    detail: str | None = None,
    type_: str | None = None,
    instance: str | None = None,
    **extensions: typing.Any,
) -> dict[str, typing.Any]:
    """RFC 9457 Problem Detailsのレスポンスボディを組み立てる。

    返り値をJSONレスポンスに変換する際は、Content-Typeへ
    ``PROBLEM_JSON_CONTENT_TYPE``を設定し、HTTPステータスコードにも
    ``status``と同じ値を設定する。

    Example:
        ``jsonify(make_problem_details(404)), 404, {"Content-Type": PROBLEM_JSON_CONTENT_TYPE}``

    Raises:
        ValueError: statusがHTTPステータスコードの範囲外か、extensionsにtypeが含まれる場合。

    """
    if not _is_valid_status(status):
        raise ValueError(f"statusがHTTPステータスコードの範囲外: {status!r}")
    if "type" in extensions:
        raise ValueError("extensionsに予約メンバーtypeは指定できない")

    effective_type = type_ if type_ is not None else "about:blank"
    if effective_type == "about:blank" and title is None:
        with contextlib.suppress(ValueError):
            title = http.HTTPStatus(status).phrase

    result: dict[str, typing.Any] = {"status": status}
    if effective_type != "about:blank":
        result["type"] = effective_type
    if title is not None:
        result["title"] = title
    if detail is not None:
        result["detail"] = detail
    if instance is not None:
        result["instance"] = instance
    result.update(extensions)
    return result


@dataclasses.dataclass(frozen=True)
class ProblemDetails:
    """RFC 9457 Problem Detailsの解析結果。"""

    type: str = "about:blank"
    title: str | None = None
    status: int | None = None
    detail: str | None = None
    instance: str | None = None
    extensions: dict[str, typing.Any] = dataclasses.field(default_factory=dict)


def parse_problem_details(body: str | bytes, base_url: str | None = None) -> ProblemDetails | None:
    """Problem DetailsのJSONボディを解析する。

    base_urlを省略した場合、相対URIのtypeとinstanceは生値のまま返す。
    """
    try:
        data = json.loads(
            body,
            parse_int=_parse_int_with_digit_limit,
            parse_constant=_reject_nonstandard_json_constant,
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    raw_type = data.get("type")
    type_: str = raw_type if isinstance(raw_type, str) else "about:blank"
    raw_instance = data.get("instance")
    instance = raw_instance if isinstance(raw_instance, str) else None
    if base_url is not None:
        with contextlib.suppress(ValueError):
            type_ = urllib.parse.urljoin(base_url, type_)
        if instance is not None:
            with contextlib.suppress(ValueError):
                instance = urllib.parse.urljoin(base_url, instance)

    reserved_members = {"type", "title", "status", "detail", "instance"}
    return ProblemDetails(
        type=type_,
        title=data.get("title") if isinstance(data.get("title"), str) else None,
        status=data.get("status") if _is_valid_status(data.get("status")) else None,
        detail=data.get("detail") if isinstance(data.get("detail"), str) else None,
        instance=instance,
        extensions={key: value for key, value in data.items() if key not in reserved_members},
    )


def _exception_response(exc: Exception) -> typing.Any:
    """例外のresponse属性を取得する。エラーレスポンスの真偽値は評価しない。"""
    return getattr(exc, "response", None)


def _exception_headers(exc: Exception) -> typing.Any:
    """responseのヘッダーを取得する。属性がない場合はNone。"""
    response = _exception_response(exc)
    return getattr(response, "headers", None) if response is not None else None


def get_problem_details_from_exception(exc: Exception) -> ProblemDetails | None:
    """例外のレスポンスからProblem Detailsを取得して解析する。

    requestsでは本文取得時に同期読み込みが発生する場合がある。未読または消費済みで
    本文を取得できない場合はNoneを返し、通信・デコード失敗は元の例外を伝播する。
    """
    response = _exception_response(exc)
    if response is None:
        return None
    headers = _exception_headers(exc)
    if headers is None:
        return None

    content_type = headers.get("Content-Type")
    if not isinstance(content_type, str):
        return None
    media_type, _ = werkzeug.http.parse_options_header(content_type)
    if media_type.lower() != PROBLEM_JSON_CONTENT_TYPE:
        return None

    try:
        content = response.content
    except RuntimeError:
        return None

    base_url = str(response.url) if hasattr(response, "url") and response.url is not None else None
    if base_url is not None and (content_location := headers.get("Content-Location")) is not None:
        with contextlib.suppress(ValueError):
            base_url = urllib.parse.urljoin(base_url, str(content_location))
    return parse_problem_details(content, base_url)


def _is_valid_status(value: object) -> typing.TypeGuard[int]:
    """HTTPステータスコードの有効範囲に含まれる整数かを返す。"""
    return isinstance(value, int) and not isinstance(value, bool) and 100 <= value <= 599


def _reject_nonstandard_json_constant(constant: str) -> typing.NoReturn:
    """JSON標準で禁止された数値定数を拒否する。"""
    raise json.JSONDecodeError("JSON標準外の数値定数", constant, 0)


def _parse_int_with_digit_limit(value: str) -> int | None:
    """実行時の整数文字列変換上限内にある値を解析する。"""
    digits = value[1:] if value.startswith("-") else value
    max_digits = sys.get_int_max_str_digits()
    if max_digits and len(digits) > max_digits:
        return None
    return int(value)


def get_status_code_from_exception(exc: Exception) -> int | None:
    """例外からステータスコードを取得する。

    少なくともrequestsとhttpxのraise_for_status()で発生する例外に対応している。
    """
    response = _exception_response(exc)
    status_code = getattr(response, "status_code", None) if response is not None else None
    if status_code is None:
        status_code = getattr(exc, "status_code", None)
    if status_code is not None:
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
    if (headers := _exception_headers(exc)) is not None:
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
        retry_at = email.utils.parsedate_to_datetime(retry_after_header)
        # parsedate_to_datetime はタイムゾーン情報付き（あるいは naive）を返す
        # retry_at が naive なら UTC とみなす
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=dt.UTC)
        # 現在の UTC 時刻を aware で取得
        now = dt.datetime.now(tz=dt.UTC)
        delta = (retry_at - now).total_seconds()
        return max(delta, 0.0)
    except Exception:
        return None


class RateLimitInfo(typing.NamedTuple):
    """X-RateLimit系ヘッダーの解析結果。"""

    limit: int | None
    remaining: int | None
    reset: int | None


def get_rate_limit_info(headers: collections.abc.Mapping[str, typing.Any]) -> RateLimitInfo:
    """X-RateLimit-Limit/-Remaining/-Resetヘッダーを解析する。

    headersは大文字小文字を区別しないMappingを想定する。
    """
    return RateLimitInfo(
        limit=_parse_nonnegative_int(headers.get("X-RateLimit-Limit")),
        remaining=_parse_nonnegative_int(headers.get("X-RateLimit-Remaining")),
        reset=_parse_nonnegative_int(headers.get("X-RateLimit-Reset")),
    )


def get_rate_limit_info_from_exception(exc: Exception) -> RateLimitInfo | None:
    """例外のレスポンスからX-RateLimit系ヘッダーを取得して解析する。"""
    if (headers := _exception_headers(exc)) is not None:
        return get_rate_limit_info(headers)
    return None


def _parse_nonnegative_int(value: typing.Any) -> int | None:
    """文字列の非負整数を解析する。"""
    if isinstance(value, str) and value.isdecimal():
        return _parse_int_with_digit_limit(value)
    return None
