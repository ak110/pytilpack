import types
import typing

import httpx
import pytest
import quart

import pytilpack.httpx
import pytilpack.quart.misc


@pytest.mark.asyncio
async def test_retry_async_client(monkeypatch: pytest.MonkeyPatch):
    waits: list[float] = []

    async def record_sleep(delay: float, **kwargs: typing.Any) -> None:
        del kwargs
        waits.append(delay)

    monkeypatch.setattr(pytilpack.httpx, "asyncio", types.SimpleNamespace(sleep=record_sleep))
    app = quart.Quart(__name__)

    counters = {
        "success": {"count": 0},
        "retry_with_header": {"count": 0},
        "retry_without_header": {"count": 0},
        "max_retries": {"count": 0},
        "other_error": {"count": 0},
    }

    @app.route("/success")
    async def success_endpoint():
        counters["success"]["count"] += 1
        return {"message": "success"}, 200

    @app.route("/retry_with_header")
    async def retry_with_header_endpoint():
        counters["retry_with_header"]["count"] += 1
        if counters["retry_with_header"]["count"] <= 2:
            return "", 429, {"Retry-After": "0.07"}
        return {"message": "success"}, 200

    @app.route("/retry_without_header")
    async def retry_without_header_endpoint():
        counters["retry_without_header"]["count"] += 1
        if counters["retry_without_header"]["count"] <= 2:
            return "", 429
        return {"message": "success"}, 200

    @app.route("/max_retries")
    async def max_retries_endpoint():
        counters["max_retries"]["count"] += 1
        return "", 429, {"Retry-After": "0.01"}

    @app.route("/other_error")
    async def other_error_endpoint():
        counters["other_error"]["count"] += 1
        return "", 500

    async with (
        pytilpack.quart.misc.run(app, port=0) as port,
        pytilpack.httpx.RetryAsyncClient(max_retries=5, initial_delay=0.01, max_jitter=0) as client,
    ):
        response = await client.get(f"http://localhost:{port}/success")
        assert response.status_code == 200
        assert response.json() == {"message": "success"}
        assert counters["success"]["count"] == 1
        assert not waits

        response = await client.get(f"http://localhost:{port}/retry_with_header")
        assert response.status_code == 200
        assert response.json() == {"message": "success"}
        assert counters["retry_with_header"]["count"] == 3
        assert waits == pytest.approx([0.07, 0.07])
        waits.clear()

        response = await client.get(f"http://localhost:{port}/retry_without_header")
        assert response.status_code == 200
        assert response.json() == {"message": "success"}
        assert counters["retry_without_header"]["count"] == 3
        assert waits == pytest.approx([0.01, 0.02])

        async with pytilpack.httpx.RetryAsyncClient(max_retries=3, initial_delay=0.01) as limited_client:
            response = await limited_client.get(f"http://localhost:{port}/max_retries")
            assert response.status_code == 429
            assert counters["max_retries"]["count"] == 3

        response = await client.get(f"http://localhost:{port}/other_error")
        assert response.status_code == 500
        assert counters["other_error"]["count"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("with_header", [True, False])
async def test_arequest_with_retry_direct(monkeypatch: pytest.MonkeyPatch, with_header: bool):
    waits: list[float] = []

    async def record_sleep(delay: float, **kwargs: typing.Any) -> None:
        del kwargs
        waits.append(delay)

    monkeypatch.setattr(pytilpack.httpx, "asyncio", types.SimpleNamespace(sleep=record_sleep))
    app = quart.Quart(__name__)
    request_count = {"count": 0}

    @app.route("/test")
    async def test_endpoint():
        request_count["count"] += 1
        if request_count["count"] <= 2:
            return "", 429, {"Retry-After": "0.07"} if with_header else {}
        return {"message": "success"}, 200

    async with pytilpack.quart.misc.run(app, port=0) as port, httpx.AsyncClient() as client:
        response = await pytilpack.httpx.arequest_with_retry(
            client, "GET", f"http://localhost:{port}/test", max_retries=3, initial_delay=0.01, max_jitter=0
        )
        assert response.status_code == 200
        assert response.json() == {"message": "success"}
        assert request_count["count"] == 3
        assert waits == pytest.approx([0.07, 0.07] if with_header else [0.01, 0.02])
