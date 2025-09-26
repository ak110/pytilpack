"""httpx関連。"""

import asyncio
import datetime
import email.utils
import logging
import random
import typing

import httpx

logger = logging.getLogger(__name__)


class RetryAsyncClient(httpx.AsyncClient):
    """429 Too Many Requests に対してリトライする AsyncClient。"""

    def __init__(
        self,
        *,
        max_retries: int = 5,
        initial_delay: float = 1.0,
        exponential_base: float = 2.0,
        max_delay: float = 30.0,
        max_jitter: float = 0.5,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.exponential_base = exponential_base
        self.max_delay = max_delay
        self.max_jitter = max_jitter

    @typing.override
    async def request(self, method: str, url: httpx.URL | str, **kwargs) -> httpx.Response:
        request_func = super().request

        class _RawAsyncClient(httpx.AsyncClient):
            async def request(self, method: str, url: httpx.URL | str, **kwargs) -> httpx.Response:
                return await request_func(method, url, **kwargs)

        return await arequest_with_retry(
            _RawAsyncClient(),
            method,
            url,
            max_retries=self.max_retries,
            initial_delay=self.initial_delay,
            exponential_base=self.exponential_base,
            max_delay=self.max_delay,
            max_jitter=self.max_jitter,
            **kwargs,
        )


async def arequest_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: httpx.URL | str,
    *,
    max_retries: int = 5,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 30.0,
    max_jitter: float = 0.5,
    **kwargs,
) -> httpx.Response:
    """429 Too Many Requests に対してリトライする非同期リクエスト関数。"""
    last_response: httpx.Response | None = None
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        resp = await client.request(method, url, **kwargs)
        last_response = resp
        if resp.status_code != 429:
            break
        wait = get_retry_after(resp)
        if wait is None:
            # ヘッダーがなければ指数バックオフ
            wait = delay * random.uniform(1.0, 1.0 + max_jitter)
            delay = min(delay * exponential_base, max_delay)
        logger.info(
            "arequest_with_retry: %s %s (retry %d/%d)",
            method,
            url,
            attempt,
            max_retries,
        )
        await asyncio.sleep(wait)
    assert last_response is not None
    return last_response


def get_retry_after(response: httpx.Response) -> float | None:
    ra = response.headers.get("Retry-After")
    if not ra:
        return None
    # 整数秒形式
    if ra.isdigit():
        return float(ra)
    # 日時形式（RFC 2822 等）を解析
    try:
        dt = email.utils.parsedate_to_datetime(ra)
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
