"""ファイル関連のユーティリティ集。"""

import logging
import pathlib

logger = logging.getLogger(__name__)


def delete_file(path: str | pathlib.Path) -> None:
    """ファイル削除。"""
    path = pathlib.Path(path)
    if path.is_file():
        path.unlink()


def get_size(path: str | pathlib.Path) -> int:
    """ファイル・ディレクトリのサイズを返す。"""
    try:
        path = pathlib.Path(path)
        if path.is_file():
            try:
                return path.stat().st_size
            except Exception:
                logger.warning(f"ファイルサイズ取得失敗: {path}", exc_info=True)
                return 0
        elif path.is_dir():
            total_size: int = 0
            try:
                for child in path.iterdir():
                    # 再帰的に子要素のサイズを加算する
                    total_size += get_size(child)
            except Exception:
                logger.warning(f"ディレクトリサイズ取得失敗: {path}", exc_info=True)
            return total_size
        else:
            return 0
    except Exception:
        logger.warning(f"ファイル・ディレクトリサイズ取得失敗: {path}", exc_info=True)
        return 0
