"""ファイル関連のユーティリティ集。"""

import pathlib


def delete_file(path: str | pathlib.Path) -> None:
    """ファイル削除。"""
    path = pathlib.Path(path)
    if path.is_file():
        path.unlink()


def get_size(path: str | pathlib.Path) -> int:
    """ファイル・ディレクトリのサイズを返す。"""
    path = pathlib.Path(path)
    if path.is_dir():
        return sum(p.stat().st_size for p in path.glob("**/*") if p.is_file())
    elif path.is_file():
        return path.stat().st_size
    else:
        return 0
