__lazy_modules__ = ["asyncio", "contextlib", "errno", "fcntl", "pathlib", "time", "typing"]

import asyncio
import contextlib
import errno
import fcntl
import pathlib
import time
import typing


def _try_acquire(fp: typing.IO) -> bool:
    try:
        fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError as e:
        if e.errno != errno.EAGAIN:
            raise
        return False


@contextlib.contextmanager
def lock(lock_path: pathlib.Path, retry_interval: float = 0.1) -> typing.Generator[None, None, None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as fp:
        while not _try_acquire(fp):
            time.sleep(retry_interval)
        try:
            yield
        finally:
            fcntl.flock(fp.fileno(), fcntl.LOCK_UN)


@contextlib.asynccontextmanager
async def alock(lock_path: pathlib.Path, retry_interval: float = 0.1) -> typing.AsyncGenerator[None, None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as fp:
        while not _try_acquire(fp):
            await asyncio.sleep(retry_interval)
        try:
            yield
        finally:
            fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
