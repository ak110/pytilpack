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
    if not candidates:
        return None
    if not accept_header:
        return candidates[0]
    accept = werkzeug.http.parse_accept_header(accept_header, werkzeug.datastructures.MIMEAccept)
    return accept.best_match(candidates)


def select_accept_language(
    header: str,
    supported: collections.abc.Sequence[str],
    default: str | None = None,
) -> str | None:
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
    if not _is_valid_status(status):
        raise ValueError(f"statusがHTTPステータスコードの範囲外: {status!r}。100以上599以下の整数を指定する")
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
    type: str = "about:blank"
    title: str | None = None
    status: int | None = None
    detail: str | None = None
    instance: str | None = None
    extensions: dict[str, typing.Any] = dataclasses.field(default_factory=dict)


def parse_problem_details(body: str | bytes, base_url: str | None = None) -> ProblemDetails | None:
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
    return getattr(exc, "response", None)


def _exception_headers(exc: Exception) -> typing.Any:
    response = _exception_response(exc)
    return getattr(response, "headers", None) if response is not None else None


def get_problem_details_from_exception(exc: Exception) -> ProblemDetails | None:
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
    return isinstance(value, int) and not isinstance(value, bool) and 100 <= value <= 599


def _reject_nonstandard_json_constant(constant: str) -> typing.NoReturn:
    raise json.JSONDecodeError("JSON標準外の数値定数", constant, 0)


def _parse_int_with_digit_limit(value: str) -> int | None:
    digits = value[1:] if value.startswith("-") else value
    max_digits = sys.get_int_max_str_digits()
    if max_digits and len(digits) > max_digits:
        return None
    return int(value)


def get_status_code_from_exception(exc: Exception) -> int | None:
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
    if (headers := _exception_headers(exc)) is not None:
        retry_after_header = headers.get("Retry-After")
        logger.info(f"Retry-After: {retry_after_header}")
        return get_retry_after(retry_after_header)
    return None


def get_retry_after(retry_after_header: str | None) -> float | None:
    if not retry_after_header:
        return None
    if re.fullmatch(r"\d+(\.\d+)?", retry_after_header):
        return float(retry_after_header)
    try:
        retry_at = email.utils.parsedate_to_datetime(retry_after_header)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=dt.UTC)
        now = dt.datetime.now(tz=dt.UTC)
        delta = (retry_at - now).total_seconds()
        return max(delta, 0.0)
    except Exception:
        return None


class RateLimitInfo(typing.NamedTuple):
    limit: int | None
    remaining: int | None
    reset: int | None


def get_rate_limit_info(headers: collections.abc.Mapping[str, typing.Any]) -> RateLimitInfo:
    return RateLimitInfo(
        limit=_parse_nonnegative_int(headers.get("X-RateLimit-Limit")),
        remaining=_parse_nonnegative_int(headers.get("X-RateLimit-Remaining")),
        reset=_parse_nonnegative_int(headers.get("X-RateLimit-Reset")),
    )


def get_rate_limit_info_from_exception(exc: Exception) -> RateLimitInfo | None:
    if (headers := _exception_headers(exc)) is not None:
        return get_rate_limit_info(headers)
    return None


def _parse_nonnegative_int(value: typing.Any) -> int | None:
    if isinstance(value, str) and value.isdecimal():
        return _parse_int_with_digit_limit(value)
    return None
