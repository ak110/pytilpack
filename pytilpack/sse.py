__lazy_modules__ = ["asyncio", "contextlib", "dataclasses", "functools", "logging", "re", "typing"]

import asyncio
import contextlib
import dataclasses
import functools
import logging
import re
import typing

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class SSE:
    data: str | None = None
    event: str | None = None
    id: str | None = None
    retry: int | None = None
    comment: str | None = None

    def __post_init__(self) -> None:
        if self.data is None and self.comment is None:
            raise ValueError("`data`と`comment`のいずれかを指定してください。")

    def __str__(self) -> str:
        return self.to_str()

    def to_str(self) -> str:
        lines = []

        if self.event is not None:
            lines.append(f"event: {self.event}")
        if self.id is not None:
            lines.append(f"id: {self.id}")
        if self.retry is not None:
            lines.append(f"retry: {self.retry}")

        # SSE仕様の行区切りは \n, \r\n, \r の3種のみ (splitlines()は対象が広すぎる)
        if self.comment is not None:
            for line in re.split(r"\r\n|\r|\n", self.comment):
                lines.append(f": {line}")
        if self.data is not None:
            for line in re.split(r"\r\n|\r|\n", self.data):
                lines.append(f"data: {line}")

        return "\n".join(lines) + "\n\n"


def generator(interval: float = 15) -> typing.Callable:

    def decorator[**P, T: str | SSE](
        func: typing.Callable[P, typing.AsyncGenerator[T, None]],
    ) -> typing.Callable[P, typing.AsyncGenerator[str, None]]:

        async def _anext(it: typing.AsyncIterator[T]) -> T:
            return await anext(it)

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> typing.AsyncGenerator[str, None]:
            loop = asyncio.get_running_loop()
            last_msg_time = loop.time()
            generator_ = func(*args, **kwargs)
            try:
                next_task: asyncio.Task[T] | None = None
                try:
                    iterator = aiter(generator_)
                    next_task = loop.create_task(_anext(iterator))

                    while True:
                        delay = interval - (loop.time() - last_msg_time)
                        try:
                            msg = await asyncio.wait_for(
                                asyncio.shield(next_task),
                                timeout=max(0.0, delay),
                            )
                            if isinstance(msg, SSE):
                                yield str(msg)
                            else:
                                yield msg.rstrip("\n") + "\n\n"
                            last_msg_time = loop.time()
                            next_task = loop.create_task(_anext(iterator))
                        except TimeoutError:
                            yield ": ping\n\n"
                            last_msg_time = loop.time()
                        except StopAsyncIteration:
                            break
                except GeneratorExit:
                    logger.info("SSE切断[1]")
                    raise
                except asyncio.CancelledError:
                    logger.info("SSE切断[2]")
                    raise
                finally:
                    if next_task is not None:
                        next_task.cancel()
                        with contextlib.suppress(StopAsyncIteration):
                            await asyncio.shield(next_task)
            finally:
                await asyncio.shield(generator_.aclose())

        return wrapper

    return decorator
