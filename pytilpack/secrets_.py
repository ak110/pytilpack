"""Pythonのユーティリティ集。"""

import pathlib
import secrets


def generate_secret_key(cache_path: str | pathlib.Path) -> bytes:
    """シークレットキーの作成/取得。

    既にcache_pathに保存済みならそれを返し、でなくば作成する。

    """
    cache_path = pathlib.Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("a+b") as secret:
        secret.seek(0)
        secret_key = secret.read()
        if not secret_key:
            secret_key = secrets.token_bytes()
            secret.write(secret_key)
            secret.flush()
        return secret_key
