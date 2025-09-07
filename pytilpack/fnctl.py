"""fcntl関連。"""

import asyncio
import contextlib
import errno
import fcntl
import pathlib
import time
import typing


@contextlib.contextmanager
def lock(lock_path: pathlib.Path, retry_interval: float = 0.1) -> typing.Generator[None, None, None]:
    """プロセス間で共有するファイルロックを取得する。

    引数:
        lock_path: ロックファイルのパス。
        retry_interval: ロックが使用中の場合に再試行するまでの待機時間（秒単位）。
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as fp:
        while True:
            try:
                fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as e:
                if e.errno != errno.EAGAIN:
                    raise
                time.sleep(retry_interval)
        try:
            yield
        finally:
            fcntl.flock(fp.fileno(), fcntl.LOCK_UN)


@contextlib.asynccontextmanager
async def alock(lock_path: pathlib.Path, retry_interval: float = 0.1) -> typing.AsyncGenerator[None, None]:
    """プロセス間で共有するファイルロックを取得する（async版）。

    引数:
        lock_path: ロックファイルのパス。
        retry_interval: ロックが使用中の場合に再試行するまでの待機時間（秒単位）。
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as fp:
        while True:
            try:
                fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as e:
                if e.errno != errno.EAGAIN:
                    raise
                await asyncio.sleep(retry_interval)
        try:
            yield
        finally:
            fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
