"""Pythonのユーティリティ集。"""

import fcntl
import pathlib
import secrets
import threading

import pytilpack.functools

_lock = threading.Lock()
"""スレッド間での排他制御用ロック。"""


@pytilpack.functools.retry()
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
        with cache_path.open("a+b") as secret:
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
                    cache_path.chmod(0o600)
                return secret_key
            finally:
                fcntl.flock(secret.fileno(), fcntl.LOCK_UN)
