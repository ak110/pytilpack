import collections.abc
import datetime as dt
import email.utils
import io
import json
import sys
import types

import httpx
import pytest
import requests

import pytilpack.http


class _ResponseStub:
    def __init__(
        self,
        *,
        headers: collections.abc.Mapping[str, str],
        content: bytes | Exception,
        url: str = "https://example.com/problems/response",
    ) -> None:
        self.headers = headers
        self._content = content
        self.url = url

    @property
    def content(self) -> bytes:
        if isinstance(self._content, Exception):
            raise self._content
        return self._content


class _ResponseException(Exception):
    def __init__(self, response: object) -> None:
        super().__init__()
        self.response = response


def _integer_over_conversion_limit() -> str:
    max_digits = sys.get_int_max_str_digits()
    if max_digits == 0:
        pytest.skip("整数文字列変換上限が無効")
    return "9" * (max_digits + 1)


def test_make_problem_details():
    assert pytilpack.http.make_problem_details(404) == {"status": 404, "title": "Not Found"}
    assert pytilpack.http.make_problem_details(404, type_="about:blank") == pytilpack.http.make_problem_details(404)
    assert pytilpack.http.make_problem_details(
        422,
        "Validation failed",
        detail="入力値が不正",
        type_="https://example.com/problems/validation",
        instance="/requests/123",
        errors=[{"field": "name"}],
    ) == {
        "type": "https://example.com/problems/validation",
        "status": 422,
        "title": "Validation failed",
        "detail": "入力値が不正",
        "instance": "/requests/123",
        "errors": [{"field": "name"}],
    }
    assert pytilpack.http.make_problem_details(499) == {"status": 499}
    assert pytilpack.http.make_problem_details(400, type_="https://example.com/problem") == {
        "type": "https://example.com/problem",
        "status": 400,
    }


@pytest.mark.parametrize("status", [99, 600, True, False])
def test_make_problem_details_rejects_invalid_status(status: int):
    match = "100以上599以下の整数を指定する" if status == 600 else None
    with pytest.raises(ValueError, match=match):
        pytilpack.http.make_problem_details(status)


@pytest.mark.parametrize("status", [100, 599])
def test_make_problem_details_accepts_boundary_status(status: int):
    assert pytilpack.http.make_problem_details(status)["status"] == status


def test_make_problem_details_rejects_type_extension():
    with pytest.raises(ValueError):
        pytilpack.http.make_problem_details(400, **{"type": "https://example.com/problem"})


def test_parse_problem_details():
    body = json.dumps(
        {
            "type": "https://example.com/problems/validation",
            "title": "Validation failed",
            "status": 422,
            "detail": "入力値が不正",
            "instance": "/requests/123",
            "errors": [{"field": "name"}],
        }
    )
    assert pytilpack.http.parse_problem_details(body) == pytilpack.http.ProblemDetails(
        type="https://example.com/problems/validation",
        title="Validation failed",
        status=422,
        detail="入力値が不正",
        instance="/requests/123",
        extensions={"errors": [{"field": "name"}]},
    )
    assert pytilpack.http.parse_problem_details("{}") == pytilpack.http.ProblemDetails()


@pytest.mark.parametrize("status", ["400", True, -1, 99, 600])
def test_parse_problem_details_ignores_invalid_status(status: object):
    body = json.dumps({"status": status})
    assert pytilpack.http.parse_problem_details(body) == pytilpack.http.ProblemDetails()


@pytest.mark.parametrize("status", [100, 599])
def test_parse_problem_details_accepts_boundary_status(status: int):
    body = json.dumps({"status": status})
    assert pytilpack.http.parse_problem_details(body) == pytilpack.http.ProblemDetails(status=status)


def test_parse_problem_details_ignores_invalid_member_types():
    body = json.dumps({"type": 1, "title": [], "detail": {}, "instance": False})
    assert pytilpack.http.parse_problem_details(body) == pytilpack.http.ProblemDetails()


@pytest.mark.parametrize("body", ["not json", "[]"])
def test_parse_problem_details_rejects_invalid_body(body: str):
    assert pytilpack.http.parse_problem_details(body) is None


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_parse_problem_details_rejects_nonstandard_json_constants(constant: str):
    assert pytilpack.http.parse_problem_details(f'{{"value": {constant}}}') is None


def test_parse_problem_details_ignores_integer_over_conversion_limit():
    body = f'{{"status": {_integer_over_conversion_limit()}, "title": "Validation failed"}}'
    assert pytilpack.http.parse_problem_details(body) == pytilpack.http.ProblemDetails(title="Validation failed")


def test_parse_problem_details_resolves_relative_uris():
    body = json.dumps({"type": "types/invalid", "instance": "requests/123"})
    assert pytilpack.http.parse_problem_details(body) == pytilpack.http.ProblemDetails(
        type="types/invalid", instance="requests/123"
    )
    assert pytilpack.http.parse_problem_details(body, "https://example.com/api/") == pytilpack.http.ProblemDetails(
        type="https://example.com/api/types/invalid",
        instance="https://example.com/api/requests/123",
    )
    assert pytilpack.http.parse_problem_details(body, "https://other.example/v1/") == pytilpack.http.ProblemDetails(
        type="https://other.example/v1/types/invalid",
        instance="https://other.example/v1/requests/123",
    )


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            '{"type": "http://[", "instance": "requests/123"}',
            pytilpack.http.ProblemDetails(
                type="http://[",
                instance="https://example.com/api/requests/123",
            ),
        ),
        (
            '{"type": "types/invalid", "instance": "http://["}',
            pytilpack.http.ProblemDetails(
                type="https://example.com/api/types/invalid",
                instance="http://[",
            ),
        ),
    ],
)
def test_parse_problem_details_preserves_uri_that_cannot_be_resolved(body: str, expected: pytilpack.http.ProblemDetails):
    assert pytilpack.http.parse_problem_details(body, "https://example.com/api/") == expected


@pytest.mark.parametrize("type_", ["about:blank", "https://example.com/problems/invalid"])
def test_parse_problem_details_preserves_absolute_type(type_: str):
    body = json.dumps({"type": type_})
    assert pytilpack.http.parse_problem_details(body, "https://example.com/api/") == pytilpack.http.ProblemDetails(type=type_)


@pytest.mark.parametrize(
    ("content_type", "expected"),
    [
        ("application/problem+json; charset=utf-8", pytilpack.http.ProblemDetails(status=400)),
        ("Application/Problem+Json", pytilpack.http.ProblemDetails(status=400)),
        ("application/problem+json-seq", None),
        ("application/json", None),
    ],
)
def test_get_problem_details_from_exception_content_type(content_type: str, expected: pytilpack.http.ProblemDetails | None):
    response = _ResponseStub(headers={"Content-Type": content_type}, content=b'{"status": 400}')
    assert pytilpack.http.get_problem_details_from_exception(_ResponseException(response)) == expected


def test_get_problem_details_from_exception_uses_content_location():
    response = _ResponseStub(
        headers={
            "Content-Type": "application/problem+json",
            "Content-Location": "../representations/problem.json",
        },
        content=b'{"type": "types/invalid", "instance": "requests/123"}',
        url="https://example.com/api/errors/response",
    )
    assert pytilpack.http.get_problem_details_from_exception(_ResponseException(response)) == pytilpack.http.ProblemDetails(
        type="https://example.com/api/representations/types/invalid",
        instance="https://example.com/api/representations/requests/123",
    )


def test_get_problem_details_from_exception_ignores_invalid_content_location():
    response = _ResponseStub(
        headers={
            "Content-Type": "application/problem+json",
            "Content-Location": "http://[",
        },
        content=b'{"type": "types/invalid", "instance": "requests/123"}',
        url="https://example.com/api/response",
    )
    assert pytilpack.http.get_problem_details_from_exception(_ResponseException(response)) == pytilpack.http.ProblemDetails(
        type="https://example.com/api/types/invalid",
        instance="https://example.com/api/requests/123",
    )


def test_get_problem_details_from_exception_propagates_content_error():
    error = requests.ConnectionError("connection lost")
    response = _ResponseStub(headers={"Content-Type": "application/problem+json"}, content=error)
    with pytest.raises(requests.ConnectionError, match="connection lost"):
        pytilpack.http.get_problem_details_from_exception(_ResponseException(response))


def test_get_problem_details_from_unread_httpx_response():
    response = httpx.Response(
        400,
        headers={"Content-Type": "application/problem+json"},
        stream=httpx.ByteStream(b'{"status": 400}'),
        request=httpx.Request("GET", "https://example.com/problem"),
    )
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        response.raise_for_status()
    assert pytilpack.http.get_problem_details_from_exception(exc_info.value) is None


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        (
            {"X-RateLimit-Limit": "100", "X-RateLimit-Remaining": "20", "X-RateLimit-Reset": "1700000000"},
            pytilpack.http.RateLimitInfo(100, 20, 1700000000),
        ),
        ({"X-RateLimit-Limit": "100"}, pytilpack.http.RateLimitInfo(100, None, None)),
        (
            {"X-RateLimit-Limit": "invalid", "X-RateLimit-Remaining": "-1", "X-RateLimit-Reset": ""},
            pytilpack.http.RateLimitInfo(None, None, None),
        ),
    ],
)
def test_get_rate_limit_info(headers: collections.abc.Mapping[str, str], expected: pytilpack.http.RateLimitInfo):
    assert pytilpack.http.get_rate_limit_info(headers) == expected


def test_get_rate_limit_info_ignores_integer_over_conversion_limit():
    value = _integer_over_conversion_limit()
    headers = {
        "X-RateLimit-Limit": value,
        "X-RateLimit-Remaining": value,
        "X-RateLimit-Reset": value,
    }
    assert pytilpack.http.get_rate_limit_info(headers) == pytilpack.http.RateLimitInfo(None, None, None)


@pytest.mark.parametrize("backend", ["requests", "httpx", "consumed-requests"])
def test_get_from_exception(backend: str) -> None:
    url = "https://example.com/problems/limited"
    headers = {
        "Retry-After": "1",
        "Content-Type": "application/problem+json",
        "X-RateLimit-Limit": "100",
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": "1700000000",
    }
    body = '{"status":429,"title":"Too Many Requests","detail":"要求回数が上限を超過"}'.encode()
    if backend == "httpx":
        httpx_response = httpx.Response(429, request=httpx.Request("GET", url), headers=headers, content=body)
        with pytest.raises(httpx.HTTPStatusError) as httpx_error:
            httpx_response.raise_for_status()
        error: Exception = httpx_error.value
    else:
        with requests.Response() as response:
            response.status_code = 429
            response.url = url
            response.headers.update(headers)
            response.raw = io.BytesIO(body)
            if backend == "consumed-requests":
                assert b"".join(response.iter_content()) == body
            with pytest.raises(requests.HTTPError) as requests_error:
                response.raise_for_status()
            error = requests_error.value

            if backend != "consumed-requests":
                assert response.content == body

    assert pytilpack.http.get_status_code_from_exception(error) == 429
    assert pytilpack.http.get_retry_after_from_exception(error) == 1.0
    assert pytilpack.http.get_rate_limit_info_from_exception(error) == pytilpack.http.RateLimitInfo(100, 0, 1700000000)
    expected = (
        None
        if backend == "consumed-requests"
        else pytilpack.http.ProblemDetails(title="Too Many Requests", status=429, detail="要求回数が上限を超過")
    )
    assert pytilpack.http.get_problem_details_from_exception(error) == expected


@pytest.mark.parametrize(
    "retry_after,expected_wait",
    [
        ("5", 5.0),
        ("0", 0.0),
        ("not_a_number", None),
        ("", None),
    ],
)
def test_get_retry_after_integer(retry_after: str, expected_wait: float | None):
    result = pytilpack.http.get_retry_after(retry_after)
    assert result == expected_wait


@pytest.mark.parametrize("offset,expected", [(5, 5.0), (-5, 0.0)])
def test_get_retry_after_datetime(monkeypatch: pytest.MonkeyPatch, offset: int, expected: float) -> None:
    now = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
    clock = types.SimpleNamespace(now=lambda *, tz: now.astimezone(tz))
    monkeypatch.setattr(pytilpack.http, "dt", types.SimpleNamespace(datetime=clock, UTC=dt.UTC))
    retry_time = now + dt.timedelta(seconds=offset)
    retry_after = email.utils.formatdate(retry_time.timestamp(), usegmt=True)

    assert pytilpack.http.get_retry_after(retry_after) == expected


def test_get_retry_after_invalid_datetime():
    result = pytilpack.http.get_retry_after("invalid datetime string")
    assert result is None


@pytest.mark.parametrize(
    "accept_header,candidates,expected",
    [
        (
            "text/html;q=0.9, application/json;q=1.0",
            ["text/html", "application/json"],
            "application/json",
        ),
        ("text/html, */*;q=0.5", ["application/json"], "application/json"),
        (
            "text/*;q=0.8, application/json;q=0.5",
            ["text/plain", "application/json"],
            "text/plain",
        ),
        ("text/html", ["application/json"], None),
        ("", ["text/html"], "text/html"),
        (
            "text/*;q=0.8, text/html;q=0.8",
            ["text/plain", "text/html"],
            "text/html",
        ),
    ],
)
def test_select_accept(
    accept_header: str,
    candidates: list[str],
    expected: str | None,
) -> None:
    assert pytilpack.http.select_accept(accept_header, candidates) == expected


@pytest.mark.parametrize(
    "header,supported,default,expected",
    [
        ("ja,en;q=0.9", ["en", "ja"], None, "ja"),
        ("en-US,en;q=0.9,ja;q=0.8", ["ja", "en"], None, "en"),
        ("fr,de;q=0.9", ["en", "ja"], "en", "en"),
        ("fr", ["en", "ja"], None, None),
        ("", ["en", "ja"], "en", "en"),
        ("ja", [], "en", "en"),
        ("ja;q=0", ["ja"], "en", "en"),
    ],
)
def test_select_accept_language(
    header: str,
    supported: list[str],
    default: str | None,
    expected: str | None,
) -> None:
    assert pytilpack.http.select_accept_language(header, supported, default) == expected
