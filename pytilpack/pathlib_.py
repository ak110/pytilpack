"""ファイル関連のユーティリティ集。"""

import datetime
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


def delete_empty_dirs(path: str | pathlib.Path, keep_root: bool = True) -> None:
    """指定したパス以下の空ディレクトリを削除する。

    Args:
        path: 対象のパス
        keep_root: Trueの場合、指定したディレクトリ自体は削除しない
    """
    path = pathlib.Path(path)
    if not path.is_dir():
        return

    for item in list(path.iterdir()):
        if item.is_dir():
            delete_empty_dirs(item, keep_root=False)

    try:
        if not keep_root:
            remaining_files = list(path.iterdir())
            if not remaining_files:
                logger.info(f"削除: {path}")
                path.rmdir()
    except Exception:
        logger.warning(f"ディレクトリの削除に失敗: {path}", exc_info=True)


def delete_old_files(
    path: str | pathlib.Path,
    before: datetime.datetime,
    delete_empty_dirs: bool = True,  # pylint: disable=redefined-outer-name
    keep_root_empty_dir: bool = True,
) -> None:
    """指定した日時より古いファイルを削除し、空になったディレクトリも削除する。

    Args:
        path: 対象のパス
        before: この日時より前に更新されたファイルを削除
        delete_empty_dirs: Trueの場合、空になったディレクトリを削除
        keep_root_empty_dir: Trueの場合、指定したディレクトリ自体は削除しない
    """
    path = pathlib.Path(path)
    if not path.exists():
        return

    if path.is_file():
        try:
            mtime = datetime.datetime.fromtimestamp(path.stat().st_mtime)
            if mtime < before:
                logger.info(f"削除: {path}")
                path.unlink()
        except Exception:
            logger.warning(f"ファイルの削除に失敗: {path}", exc_info=True)
    elif path.is_dir():
        # 再帰的に子要素を処理
        for item in list(path.iterdir()):
            delete_old_files(item, before, delete_empty_dirs, keep_root_empty_dir=False)

        # 空になったディレクトリを削除
        if delete_empty_dirs and not keep_root_empty_dir:
            try:
                remaining_files = list(path.iterdir())
                if not remaining_files:
                    logger.info(f"削除: {path}")
                    path.rmdir()
            except Exception:
                logger.warning(f"ディレクトリの削除に失敗: {path}", exc_info=True)
