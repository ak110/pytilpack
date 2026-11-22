__lazy_modules__ = ["dataclasses", "random"]

import dataclasses
import random


@dataclasses.dataclass
class Backoff:
    delay: float
    exponential_base: float
    max_delay: float
    max_jitter: float

    def wait(self, retry_after: float | None) -> float:
        return retry_after if retry_after is not None else self.delay * random.uniform(1.0, 1.0 + self.max_jitter)

    def advance(self) -> None:
        self.delay = min(self.delay * self.exponential_base, self.max_delay)
