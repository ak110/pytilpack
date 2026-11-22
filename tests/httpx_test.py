import types

import httpx
import pytest

import pytilpack.httpx


@pytest.fixture(name="waits")
def _waits(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    delays: list[float] = []

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr(pytilpack.httpx, "asyncio", types.SimpleNamespace(sleep=record_sleep))
    return delays


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "statuses,retry_after,attempts,expected_status,expected_waits",
    [
        ([200], None, 3, 200, []),
        ([429, 429, 200], "0.07", 3, 200, [0.07, 0.07]),
        ([429, 429, 200], None, 3, 200, [0.01, 0.02]),
        ([429, 429], "0.01", 2, 429, [0.01]),
        ([500], None, 3, 500, []),
    ],
)
async def test_retry_async_client(
    waits: list[float],
    statuses: list[int],
    retry_after: str | None,
    attempts: int,
    expected_status: int,
    expected_waits: list[float],
) -> None:
    sent: list[tuple[str, int]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        status = statuses[min(len(sent), len(statuses) - 1)]
        sent.append((str(request.url), len(waits)))
        headers = {"Retry-After": retry_after} if status == 429 and retry_after is not None else {}
        return httpx.Response(status, headers=headers, json={"status": status})

    url = "https://example.com/test?mode=retry"
    async with pytilpack.httpx.RetryAsyncClient(
        transport=httpx.MockTransport(respond), max_retries=attempts, initial_delay=0.01, max_jitter=0
    ) as client:
        response = await client.get("https://example.com/test", params={"mode": "retry"})

    assert response.status_code == expected_status
    assert response.json() == {"status": expected_status}
    assert sent == [(url, completed_waits) for completed_waits in range(len(statuses))]
    assert waits[: sent[-1][1]] == pytest.approx(expected_waits)


@pytest.mark.asyncio
@pytest.mark.parametrize("with_header", [True, False])
async def test_arequest_with_retry_direct(waits: list[float], with_header: bool) -> None:
    sent: list[tuple[str, str]] = []
    statuses = iter((429, 429, 200))

    def respond(request: httpx.Request) -> httpx.Response:
        sent.append((request.method, request.url.path))
        status = next(statuses)
        if status == 429:
            return httpx.Response(status, headers={"Retry-After": "0.07"} if with_header else {})
        return httpx.Response(status, json={"message": "success"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        response = await pytilpack.httpx.arequest_with_retry(
            client, "GET", "https://example.com/test", max_retries=3, initial_delay=0.01, max_jitter=0
        )

    assert response.status_code == 200
    assert response.json() == {"message": "success"}
    assert sent == [("GET", "/test")] * 3
    assert waits == pytest.approx([0.07, 0.07] if with_header else [0.01, 0.02])
