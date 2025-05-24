"""ファイル関連のユーティリティ集。"""

import datetime
import filecmp
import logging
import pathlib
import shutil

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


def sync(
    src: str | pathlib.Path, dst: str | pathlib.Path, delete: bool = False
) -> None:
    """コピー元からコピー先へ同期する。

    Args:
        src: コピー元のパス
        dst: コピー先のパス
        delete: Trueの場合、コピー元に存在しないコピー先のファイル・ディレクトリを削除

    """
    src = pathlib.Path(src)
    dst = pathlib.Path(dst)

    if not src.exists():
        logger.warning(f"コピー元が存在しません: {src}")
        return

    if not dst.exists():
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"コピー: {src} -> {dst}")
            shutil.copy2(src, dst)
        else:
            logger.info(f"作成: {dst}")
            dst.mkdir(parents=True)

    if src.is_file():
        if dst.is_file():
            # ファイルのメタデータが一致しなければコピー
            if not filecmp.cmp(src, dst):
                logger.info(f"コピー: {src} -> {dst}")
                shutil.copy2(src, dst)
        else:
            # コピー先がファイルでない場合はいったん削除
            if dst.exists():
                if dst.is_dir():
                    logger.info(f"削除: {dst}")
                    shutil.rmtree(dst)
                else:
                    logger.info(f"削除: {dst}")
                    dst.unlink()
            dst.parent.mkdir(parents=True, exist_ok=True)
            # コピー
            logger.info(f"コピー: {src} -> {dst}")
            shutil.copy2(src, dst)
    elif src.is_dir():
        # コピー先がファイルでない場合はいったん削除
        if not dst.is_dir():
            if dst.exists():
                logger.info(f"削除: {dst}")
                if dst.is_dir():
                    shutil.rmtree(dst)
                else:
                    dst.unlink()
            logger.info(f"作成: {dst}")
            dst.mkdir(parents=True)

        # コピー元のファイル・ディレクトリを同期
        for src_child in src.iterdir():
            dst_child = dst / src_child.name
            sync(src_child, dst_child, delete)

        # コピー元に存在しないコピー先のファイル・ディレクトリを削除
        if delete:
            for dst_child in dst.iterdir():
                src_child = src / dst_child.name
                if not src_child.exists():
                    logger.info(f"削除: {dst_child}")
                    if dst_child.is_dir():
                        shutil.rmtree(dst_child)
                    else:
                        dst_child.unlink()


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
