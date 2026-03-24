"""テストコード。"""

import datetime
import email.utils

import httpx
import pytest
import quart
import requests

import pytilpack.http
import pytilpack.quart.misc


@pytest.mark.asyncio
async def test_get_from_exception():
    """get_status_code_from_exception / get_retry_after_from_exception関数のテスト。"""

    app = quart.Quart(__name__)

    @app.route("/retry_with_header")
    async def retry_with_header_endpoint():
        """Retry-Afterヘッダーありの429エラーエンドポイント。"""
        return "", 429, {"Retry-After": "1"}

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
