"""リトライ待機時間の共通計算。"""

__lazy_modules__ = ["dataclasses", "random"]

import dataclasses
import random


@dataclasses.dataclass
class Backoff:
    """指数バックオフの待機時間を管理する。"""

    delay: float
    exponential_base: float
    max_delay: float
    max_jitter: float

    def wait(self, retry_after: float | None) -> float:
        """Retry-Afterを優先し、無い場合だけジッターを生成する。"""
        return retry_after if retry_after is not None else self.delay * random.uniform(1.0, 1.0 + self.max_jitter)

    def advance(self) -> None:
        """指数バックオフを次の待機時間へ進める。"""
        self.delay = min(self.delay * self.exponential_base, self.max_delay)
