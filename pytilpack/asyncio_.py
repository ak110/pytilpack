"""非同期I/O関連。"""

import asyncio
import logging
import typing

logger = logging.getLogger(__name__)

T = typing.TypeVar("T")


def run(coro: typing.Awaitable[T]) -> T:
    """非同期関数を実行する。"""
    # https://github.com/microsoftgraph/msgraph-sdk-python/issues/366#issuecomment-1830756182
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        logger.debug("EventLoop Error", exc_info=True)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)
