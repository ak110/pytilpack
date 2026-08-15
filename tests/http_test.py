"""テストコード。"""

import collections.abc
import datetime
import email.utils
import json

import httpx
import pytest
import quart
import requests

import pytilpack.http
import pytilpack.quart.misc


class _ResponseStub:
    """例外レスポンス用のスタブ。"""

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
        """本文を返すか、指定された例外を送出する。"""
        if isinstance(self._content, Exception):
            raise self._content
        return self._content


class _ResponseException(Exception):
    """response属性を持つ例外のスタブ。"""

    def __init__(self, response: object) -> None:
        super().__init__()
        self.response = response


def test_make_problem_details():
    """Problem Detailsの生成時に標準メンバーと拡張メンバーを組み立てる。"""
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
    """Problem Detailsの生成時に無効なHTTPステータスコードを拒否する。"""
    with pytest.raises(ValueError):
        pytilpack.http.make_problem_details(status)


@pytest.mark.parametrize("status", [100, 599])
def test_make_problem_details_accepts_boundary_status(status: int):
    """Problem Detailsの生成時にHTTPステータスコードの境界値を受理する。"""
    assert pytilpack.http.make_problem_details(status)["status"] == status


def test_make_problem_details_rejects_type_extension():
    """Problem Detailsの生成時にtype拡張メンバーとの衝突を拒否する。"""
    with pytest.raises(ValueError):
        pytilpack.http.make_problem_details(400, **{"type": "https://example.com/problem"})


def test_parse_problem_details():
    """Problem Detailsの標準メンバーと拡張メンバーを解析する。"""
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


@pytest.mark.parametrize("status", ["400", True, 99, 600])
def test_parse_problem_details_ignores_invalid_status(status: object):
    """Problem Detailsの型または範囲が不正なstatusを無視する。"""
    body = json.dumps({"status": status})
    assert pytilpack.http.parse_problem_details(body) == pytilpack.http.ProblemDetails()


@pytest.mark.parametrize("status", [100, 599])
def test_parse_problem_details_accepts_boundary_status(status: int):
    """Problem Detailsのstatus境界値を受理する。"""
    body = json.dumps({"status": status})
    assert pytilpack.http.parse_problem_details(body) == pytilpack.http.ProblemDetails(status=status)


def test_parse_problem_details_ignores_invalid_member_types():
    """Problem Detailsの型が不正な標準メンバーを既定値へ戻す。"""
    body = json.dumps({"type": 1, "title": [], "detail": {}, "instance": False})
    assert pytilpack.http.parse_problem_details(body) == pytilpack.http.ProblemDetails()


@pytest.mark.parametrize("body", ["not json", "[]"])
def test_parse_problem_details_rejects_invalid_body(body: str):
    """JSONオブジェクトでないProblem Details本文を拒否する。"""
    assert pytilpack.http.parse_problem_details(body) is None


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_parse_problem_details_rejects_nonstandard_json_constants(constant: str):
    """JSON標準で禁止された数値定数を含む本文を拒否する。"""
    assert pytilpack.http.parse_problem_details(f'{{"value": {constant}}}') is None


def test_parse_problem_details_rejects_integer_over_conversion_limit():
    """整数文字列変換上限を超えるstatusを含む本文を拒否する。"""
    assert pytilpack.http.parse_problem_details(f'{{"status": {"9" * 4301}}}') is None


def test_parse_problem_details_resolves_relative_uris():
    """Problem Detailsの相対URIを指定された基底URIで解決する。"""
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
    """解決できないURIだけを生値のまま保持する。"""
    assert pytilpack.http.parse_problem_details(body, "https://example.com/api/") == expected


@pytest.mark.parametrize("type_", ["about:blank", "https://example.com/problems/invalid"])
def test_parse_problem_details_preserves_absolute_type(type_: str):
    """Problem Detailsの絶対URIまたはabout:blankを基底URIで変更しない。"""
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
    """Problem Detailsのメディアタイプをパラメーター分離と大小文字正規化後に判定する。"""
    response = _ResponseStub(headers={"Content-Type": content_type}, content=b'{"status": 400}')
    assert pytilpack.http.get_problem_details_from_exception(_ResponseException(response)) == expected


def test_get_problem_details_from_exception_uses_content_location():
    """Problem Detailsの基底URIにContent-Locationを優先する。"""
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
    """不正なContent-LocationではレスポンスURLを基底URIに使用する。"""
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
    """Problem Details本文の取得中に発生した通信例外を伝播する。"""
    error = requests.ConnectionError("connection lost")
    response = _ResponseStub(headers={"Content-Type": "application/problem+json"}, content=error)
    with pytest.raises(requests.ConnectionError, match="connection lost"):
        pytilpack.http.get_problem_details_from_exception(_ResponseException(response))


def test_get_problem_details_from_unread_httpx_response():
    """未読のhttpxレスポンスから本文を取得できない場合はNoneを返す。"""
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
    """X-RateLimit系ヘッダーの非負整数を解析する。"""
    assert pytilpack.http.get_rate_limit_info(headers) == expected


def test_get_rate_limit_info_ignores_integer_over_conversion_limit():
    """整数文字列変換上限を超えるX-RateLimit値を無視する。"""
    value = "9" * 4301
    headers = {
        "X-RateLimit-Limit": value,
        "X-RateLimit-Remaining": value,
        "X-RateLimit-Reset": value,
    }
    assert pytilpack.http.get_rate_limit_info(headers) == pytilpack.http.RateLimitInfo(None, None, None)


@pytest.mark.asyncio
async def test_get_from_exception():
    """HTTP例外からステータス、再試行、Problem Details、レート制限を取得する。"""

    app = quart.Quart(__name__)

    @app.route("/retry_with_header")
    async def retry_with_header_endpoint():
        """Retry-Afterヘッダーありの429エラーエンドポイント。"""
        return "", 429, {"Retry-After": "1"}

    @app.route("/problem")
    async def problem_endpoint():
        """Problem Detailsとレート制限ヘッダーを返すエンドポイント。"""
        status = 429
        body = pytilpack.http.make_problem_details(status, detail="要求回数が上限を超過")
        return (
            body,
            status,
            {
                "Content-Type": pytilpack.http.PROBLEM_JSON_CONTENT_TYPE,
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "1700000000",
            },
        )

    async with pytilpack.quart.misc.run(app, port=5003):
        # requestsの例外のテスト
        try:
            r1 = requests.get("http://localhost:5003/retry_with_header", timeout=5)
            print(f"{r1.status_code=}, {r1.headers=}")
            r1.raise_for_status()
            pytest.fail("Expected HTTPError was not raised")
        except requests.HTTPError as e:
            assert pytilpack.http.get_status_code_from_exception(e) == 429
            assert pytilpack.http.get_retry_after_from_exception(e) == 1.0

        # httpxの例外のテスト
        try:
            async with httpx.AsyncClient() as client:
                r2 = await client.get("http://localhost:5003/retry_with_header", timeout=5)
                print(f"{r2.status_code=}, {r2.headers=}")
                r2.raise_for_status()
            pytest.fail("Expected HTTPStatusError was not raised")
        except httpx.HTTPStatusError as e:
            assert pytilpack.http.get_status_code_from_exception(e) == 429
            assert pytilpack.http.get_retry_after_from_exception(e) == 1.0

        try:
            problem_response = requests.get("http://localhost:5003/problem", timeout=5)
            problem_response.raise_for_status()
            pytest.fail("Expected HTTPError was not raised")
        except requests.HTTPError as e:
            assert e.response.status_code == 429
            assert e.response.headers["Content-Type"].startswith(pytilpack.http.PROBLEM_JSON_CONTENT_TYPE)
            assert pytilpack.http.get_problem_details_from_exception(e) == pytilpack.http.ProblemDetails(
                title="Too Many Requests",
                status=429,
                detail="要求回数が上限を超過",
            )
            assert pytilpack.http.get_rate_limit_info_from_exception(e) == pytilpack.http.RateLimitInfo(100, 0, 1700000000)

        try:
            async with httpx.AsyncClient() as client:
                problem_response_async = await client.get("http://localhost:5003/problem", timeout=5)
                problem_response_async.raise_for_status()
            pytest.fail("Expected HTTPStatusError was not raised")
        except httpx.HTTPStatusError as e:
            assert e.response.status_code == 429
            assert e.response.headers["Content-Type"].startswith(pytilpack.http.PROBLEM_JSON_CONTENT_TYPE)
            assert pytilpack.http.get_problem_details_from_exception(e) == pytilpack.http.ProblemDetails(
                title="Too Many Requests",
                status=429,
                detail="要求回数が上限を超過",
            )
            assert pytilpack.http.get_rate_limit_info_from_exception(e) == pytilpack.http.RateLimitInfo(100, 0, 1700000000)

        with requests.get("http://localhost:5003/problem", timeout=5, stream=True) as streamed_response:
            list(streamed_response.iter_content())
            with pytest.raises(requests.HTTPError) as exc_info:
                streamed_response.raise_for_status()
            assert pytilpack.http.get_problem_details_from_exception(exc_info.value) is None


@pytest.mark.parametrize(
    "retry_after,expected_wait",
    [
        ("5", 5.0),  # 整数秒形式
        ("0", 0.0),  # 0秒
        ("not_a_number", None),  # 無効な値
        ("", None),  # 空文字
    ],
)
def test_get_retry_after_integer(retry_after: str, expected_wait: float | None):
    """_get_retry_after関数の整数秒形式テスト。"""
    result = pytilpack.http.get_retry_after(retry_after)
    assert result == expected_wait


def test_get_retry_after_datetime():
    """_get_retry_after関数の日時形式テスト。"""
    # 現在時刻から5秒後の日時文字列を作成
    future_time = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=5)
    retry_after = email.utils.formatdate(future_time.timestamp(), usegmt=True)

    result = pytilpack.http.get_retry_after(retry_after)

    # 約5秒（誤差±1秒程度を許容）
    assert result is not None
    assert 4.0 <= result <= 6.0


def test_get_retry_after_past_datetime():
    """_get_retry_after関数の過去の日時形式テスト。"""
    # 現在時刻から5秒前の日時文字列を作成
    past_time = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(seconds=5)
    retry_after = email.utils.formatdate(past_time.timestamp(), usegmt=True)

    result = pytilpack.http.get_retry_after(retry_after)

    # 過去の時刻の場合は0.0を返す
    assert result == 0.0


def test_get_retry_after_invalid_datetime():
    """_get_retry_after関数の無効な日時形式テスト。"""
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
        ("", ["text/html"], "text/html"),  # 空 = 何でも受け入れる
        (
            "text/*;q=0.8, text/html;q=0.8",
            ["text/plain", "text/html"],
            "text/html",  # specificity考慮
        ),
    ],
)
def test_select_accept(
    accept_header: str,
    candidates: list[str],
    expected: str | None,
) -> None:
    """select_acceptのテスト。"""
    assert pytilpack.http.select_accept(accept_header, candidates) == expected


@pytest.mark.parametrize(
    "header,supported,default,expected",
    [
        # 基本的なマッチング
        ("ja,en;q=0.9", ["en", "ja"], None, "ja"),
        ("en-US,en;q=0.9,ja;q=0.8", ["ja", "en"], None, "en"),
        # マッチなし → default
        ("fr,de;q=0.9", ["en", "ja"], "en", "en"),
        ("fr", ["en", "ja"], None, None),
        # 空ヘッダー → default
        ("", ["en", "ja"], "en", "en"),
        # 空サポートリスト → default
        ("ja", [], "en", "en"),
        # q=0（拒否）のみ
        ("ja;q=0", ["ja"], "en", "en"),
    ],
)
def test_select_accept_language(
    header: str,
    supported: list[str],
    default: str | None,
    expected: str | None,
) -> None:
    """select_accept_languageのテスト。"""
    assert pytilpack.http.select_accept_language(header, supported, default) == expected
