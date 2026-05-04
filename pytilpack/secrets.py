"""Pythonのユーティリティ集。"""

import fcntl
import os
import pathlib
import secrets
import threading

import pytilpack.functools

_lock = threading.Lock()
"""スレッド間での排他制御用ロック。"""


@pytilpack.functools.retry(includes=[OSError])
def generate_secret_key(cache_path: str | pathlib.Path, nbytes: int | None = None) -> bytes:
    """シークレットキーの作成/取得。

    既にcache_pathに保存済みならそれを返し、でなくば作成する。

    排他制御の都合上、Linux/Unix系OSでのみ動作する。

    Args:
        cache_path: シークレットキーを保存するパス。
        nbytes: 生成するシークレットキーのバイト数。

    """
    cache_path = pathlib.Path(cache_path)

    with _lock:  # スレッド間の排他制御
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        # os.openを使い作成時点から0o600を保証する（pathlib.open/open()はumaskの影響を受けるため）
        fd = os.open(cache_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            with os.fdopen(fd, "r+b") as secret:
                fd = -1  # fdopen成功でfd所有権がsecretに移った
                # プロセス間の排他制御
                fcntl.flock(secret.fileno(), fcntl.LOCK_EX)
                try:
                    secret.seek(0)
                    secret_key = secret.read()
                    if not secret_key:
                        secret_key = secrets.token_bytes(nbytes)
                        secret.seek(0)
                        secret.truncate()
                        secret.write(secret_key)
                        secret.flush()
                    return secret_key
                finally:
                    fcntl.flock(secret.fileno(), fcntl.LOCK_UN)
        finally:
            if fd >= 0:
                os.close(fd)
