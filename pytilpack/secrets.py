"""Unixのファイルロックでシークレットキーを生成・保存する支援。"""

__lazy_modules__ = ["fcntl", "os", "pathlib", "pytilpack.functools", "secrets", "threading"]

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
    """シークレットキーを取得または生成する。

    cache_pathに保存済みの場合はそれを返し、未存在の場合は生成してから保存する。

    排他制御の都合上、Linux/Unix系OSでのみ動作する。

    Args:
        cache_path: シークレットキーを保存するパス。
        nbytes: 生成するシークレットキーのバイト数。

    """
    cache_path = pathlib.Path(cache_path)

    with _lock:  # スレッド間の排他制御
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        def opener(path: str, flags: int) -> int:
            # 作成時から0o600を保証し、既存の内容をロック取得まで保持する。
            return os.open(path, flags | os.O_CREAT, 0o600)

        with open(cache_path, "r+b", opener=opener) as secret:
            fcntl.flock(secret.fileno(), fcntl.LOCK_EX)
            try:
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
