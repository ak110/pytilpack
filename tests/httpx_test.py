"""テストコード。"""

import asyncio
import datetime
import email.utils

import httpx
import pytest
import quart

import pytilpack.httpx
import pytilpack.quart.misc


@pytest.mark.asyncio
async def test_retry_async_client():
    """RetryAsyncClientの包括的テスト。"""
    app = quart.Quart(__name__)

    # テスト用のカウンター
    counters = {
        "success": {"count": 0},
        "retry_with_header": {"count": 0},
        "retry_without_header": {"count": 0},
        "max_retries": {"count": 0},
        "other_error": {"count": 0},
    }

    @app.route("/success")
    async def success_endpoint():
        """正常系エンドポイント。"""
        counters["success"]["count"] += 1
        return {"message": "success"}, 200

    @app.route("/retry_with_header")
    async def retry_with_header_endpoint():
        """Retry-Afterヘッダーありの429エラーエンドポイント。"""
        counters["retry_with_header"]["count"] += 1
        if counters["retry_with_header"]["count"] <= 2:
            return "", 429, {"Retry-After": "0.1"}
        return {"message": "success"}, 200

    @app.route("/retry_without_header")
    async def retry_without_header_endpoint():
        """Retry-Afterヘッダーなしの429エラーエンドポイント。"""
        counters["retry_without_header"]["count"] += 1
        if counters["retry_without_header"]["count"] <= 2:
            return "", 429
        return {"message": "success"}, 200

    @app.route("/max_retries")
    async def max_retries_endpoint():
        """最大リトライ回数を超える429エラーエンドポイント。"""
        counters["max_retries"]["count"] += 1
        return "", 429, {"Retry-After": "0.01"}

    @app.route("/other_error")
    async def other_error_endpoint():
        """429以外のエラーエンドポイント。"""
        counters["other_error"]["count"] += 1
        return "", 500

    async with (
        pytilpack.quart.misc.run(app, port=5001),
        pytilpack.httpx.RetryAsyncClient(max_retries=5, initial_delay=0.01) as client,
    ):
        # 正常系のテスト
        response = await client.get("http://localhost:5001/success")
        assert response.status_code == 200
        assert response.json() == {"message": "success"}
        assert counters["success"]["count"] == 1

        # Retry-Afterヘッダーありの429エラーリトライテスト
        start_time = asyncio.get_event_loop().time()
        response = await client.get("http://localhost:5001/retry_with_header")
        elapsed_time = asyncio.get_event_loop().time() - start_time
        assert response.status_code == 200
        assert response.json() == {"message": "success"}
        assert counters["retry_with_header"]["count"] == 3
        assert elapsed_time >= 0.04  # Retry-Afterヘッダーで約0.05秒の遅延（ヘッダー優先、誤差考慮）

        # Retry-Afterヘッダーなしの429エラーリトライテスト（指数バックオフ）
        start_time = asyncio.get_event_loop().time()
        response = await client.get("http://localhost:5001/retry_without_header")
        elapsed_time = asyncio.get_event_loop().time() - start_time
        assert response.status_code == 200
        assert response.json() == {"message": "success"}
        assert counters["retry_without_header"]["count"] == 3
        assert elapsed_time >= 0.02  # 指数バックオフで約0.03秒の遅延（0.01 + 0.02、誤差考慮）

        # 最大リトライ回数を超えた場合のテスト
        async with pytilpack.httpx.RetryAsyncClient(max_retries=3, initial_delay=0.01) as limited_client:
            response = await limited_client.get("http://localhost:5001/max_retries")
            assert response.status_code == 429
            assert counters["max_retries"]["count"] == 3

        # 429以外のエラーの場合はリトライしないテスト
        response = await client.get("http://localhost:5001/other_error")
        assert response.status_code == 500
        assert counters["other_error"]["count"] == 1


@pytest.mark.asyncio
async def test_arequest_with_retry_direct():
    """arequest_with_retry関数の直接テスト。"""
    app = quart.Quart(__name__)
    request_count = {"count": 0}

    @app.route("/test")
    async def test_endpoint():
        """テスト用エンドポイント。"""
        request_count["count"] += 1
        if request_count["count"] <= 1:
            return "", 429, {"Retry-After": "0.05"}
        return {"message": "success"}, 200

    async with pytilpack.quart.misc.run(app, port=5002), httpx.AsyncClient() as client:
        response = await pytilpack.httpx.arequest_with_retry(
            client, "GET", "http://localhost:5002/test", max_retries=3, initial_delay=0.01
        )
        assert response.status_code == 200
        assert response.json() == {"message": "success"}
        assert request_count["count"] == 2


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
    response = httpx.Response(200, headers={"Retry-After": retry_after} if retry_after else {})
    result = pytilpack.httpx.get_retry_after(response)
    assert result == expected_wait


def test_get_retry_after_datetime():
    """_get_retry_after関数の日時形式テスト。"""
    # 現在時刻から5秒後の日時文字列を作成
    future_time = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=5)
    retry_after = email.utils.formatdate(future_time.timestamp(), usegmt=True)

    response = httpx.Response(200, headers={"Retry-After": retry_after})
    result = pytilpack.httpx.get_retry_after(response)

    # 約5秒（誤差±1秒程度を許容）
    assert result is not None
    assert 4.0 <= result <= 6.0


def test_get_retry_after_past_datetime():
    """_get_retry_after関数の過去の日時形式テスト。"""
    # 現在時刻から5秒前の日時文字列を作成
    past_time = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(seconds=5)
    retry_after = email.utils.formatdate(past_time.timestamp(), usegmt=True)

    response = httpx.Response(200, headers={"Retry-After": retry_after})
    result = pytilpack.httpx.get_retry_after(response)

    # 過去の時刻の場合は0.0を返す
    assert result == 0.0


def test_get_retry_after_invalid_datetime():
    """_get_retry_after関数の無効な日時形式テスト。"""
    response = httpx.Response(200, headers={"Retry-After": "invalid datetime string"})
    result = pytilpack.httpx.get_retry_after(response)
    assert result is None
