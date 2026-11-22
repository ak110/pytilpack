__lazy_modules__ = ["fcntl", "os", "pathlib", "pytilpack.functools", "secrets", "threading"]

import fcntl
import os
import pathlib
import secrets
import threading

import pytilpack.functools

_lock = threading.Lock()


@pytilpack.functools.retry(includes=[OSError])
def generate_secret_key(cache_path: str | pathlib.Path, nbytes: int | None = None) -> bytes:
    cache_path = pathlib.Path(cache_path)

    with _lock:
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        def opener(path: str, flags: int) -> int:
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
