"""レートリミッター。

httpx.py (429リトライ) やfunctools.py (retry/max_concurrency) を補完する
プロアクティブなレート制限機能。
"""

import asyncio
import time
import typing


class RateLimiter:
    """トークンバケット方式のレートリミッター。

    使用例::

        ```python
        limiter = RateLimiter(rate=10, per=1.0)  # 10リクエスト/秒
        async with limiter:
            await make_request()
        ```
    """

    def __init__(self, rate: float, per: float = 1.0) -> None:
        """初期化。

        Args:
            rate: 期間あたりの許可数。
            per: 期間（秒）。
        """
        self._max_tokens = rate
        self._tokens = rate  # 満タンで開始
        self._refill_rate = rate / per  # トークン/秒
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """トークンを1つ消費する。不足時は補充されるまで待機。"""
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                # 1トークン分の待機時間を算出
                wait_time = (1.0 - self._tokens) / self._refill_rate
            # ロック外でスリープし、他のコルーチンをブロックしない
            await asyncio.sleep(wait_time)

    async def __aenter__(self) -> "RateLimiter":  # noqa: D105
        await self.acquire()
        return self

    async def __aexit__(self, *args: typing.Any) -> None:  # noqa: D105
        del args  # noqa

    def _refill(self) -> None:
        """経過時間に基づいてトークンを補充する。ロック内で呼び出すこと。"""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._max_tokens, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now
