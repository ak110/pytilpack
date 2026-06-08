"""ファイル関連のユーティリティ集。"""

import dataclasses
import datetime
import logging
import os
import pathlib
import shutil
import stat

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class RmtreeResult:
    """rmtree()の削除結果。"""

    files: int = 0
    dirs: int = 0
    total_size: int = 0
    errors: int = 0

    def __add__(self, other: "RmtreeResult") -> "RmtreeResult":
        """フィールド同士を加算した新しい結果を返す。"""
        if not isinstance(other, RmtreeResult):
            return NotImplemented
        return RmtreeResult(
            files=self.files + other.files,
            dirs=self.dirs + other.dirs,
            total_size=self.total_size + other.total_size,
            errors=self.errors + other.errors,
        )

    def __radd__(self, other: int) -> "RmtreeResult":
        """sum()の初期値0との加算を許容し、それ以外はNotImplementedを返す。"""
        if other == 0:
            return self
        return NotImplemented


@dataclasses.dataclass
class _RmtreeStats:
    """rmtree()内部で集計に用いるミュータブルなアキュムレータ。"""

    files: int = 0
    dirs: int = 0
    total_size: int = 0
    errors: int = 0


def append_text(path: str | pathlib.Path, data: str, encoding: str = "utf-8", errors: str = "strict") -> None:
    """ファイルにテキストを追記する。"""
    path = pathlib.Path(path)
    with path.open("a", encoding=encoding, errors=errors) as f:
        f.write(data)


def append_bytes(path: str | pathlib.Path, data: bytes) -> None:
    """ファイルにバイトを追記する。"""
    path = pathlib.Path(path)
    with path.open("ab") as f:
        f.write(data)


def delete_file(path: str | pathlib.Path) -> None:
    """ファイルを削除する。"""
    path = pathlib.Path(path)
    if path.is_file():
        path.unlink()


def rmtree(path: str | pathlib.Path, ignore_errors: bool = False) -> RmtreeResult:
    """ディレクトリを再帰的に削除する。読み取り専用ファイルも削除する。

    パスが存在しない場合は空の結果を返す。
    ディレクトリへのシンボリックリンクをトップに渡した場合はNotADirectoryErrorを送出する。
    ファイル本体またはファイルへのシンボリックリンクの場合は単一ファイルとして削除する。

    Args:
        path: 対象パス
        ignore_errors: Trueなら削除に失敗してもerrorsへ計上して走査を続行する

    Returns:
        削除したファイル数・ディレクトリ数・合計サイズ・エラー数。
    """
    path = pathlib.Path(path)
    stats = _RmtreeStats()

    if path.is_symlink():
        # シンボリックリンクの解決先がディレクトリならshutil.rmtree同様に例外
        if path.is_dir():
            raise NotADirectoryError(f"Cannot call rmtree on a symbolic link: {path}")
        # ファイルへのシンボリックリンク（または解決先が存在しないリンク）は単一ファイル扱い
        _remove_file(path, stats, ignore_errors)
        return _to_result(stats)

    if not path.exists():
        return _to_result(stats)

    if not path.is_dir():
        _remove_file(path, stats, ignore_errors)
        return _to_result(stats)

    def on_walk_error(exc: OSError) -> None:
        if ignore_errors:
            stats.errors += 1
        else:
            raise exc

    # ``Path.walk(follow_symlinks=False)`` はシンボリックリンクを ``filenames`` に分類する。
    # ディレクトリへのシンボリックリンクも追従されず ``filenames`` 経由で ``_remove_file`` が処理する。
    for root, _dirnames, filenames in path.walk(top_down=False, on_error=on_walk_error):
        for fname in filenames:
            _remove_file(root / fname, stats, ignore_errors)
        _remove_dir(root, stats, ignore_errors)

    return _to_result(stats)


def _to_result(stats: _RmtreeStats) -> RmtreeResult:
    return RmtreeResult(files=stats.files, dirs=stats.dirs, total_size=stats.total_size, errors=stats.errors)


def _remove_file(path: pathlib.Path, stats: _RmtreeStats, ignore_errors: bool) -> None:
    """ファイル（またはシンボリックリンク）を削除し統計を更新する。"""
    is_link = path.is_symlink()
    try:
        size = 0 if is_link else path.stat().st_size
    except OSError:
        if ignore_errors:
            stats.errors += 1
            return
        raise

    try:
        path.unlink()
    except PermissionError:
        # 読み取り専用属性をクリアしてリトライする
        try:
            os.chmod(path, stat.S_IWRITE)
            path.unlink()
        except OSError:
            if ignore_errors:
                stats.errors += 1
                return
            raise
    except OSError:
        if ignore_errors:
            stats.errors += 1
            return
        raise

    stats.files += 1
    stats.total_size += size


def _remove_dir(path: pathlib.Path, stats: _RmtreeStats, ignore_errors: bool) -> None:
    """空ディレクトリを削除し統計を更新する。"""
    try:
        path.rmdir()
    except PermissionError:
        try:
            os.chmod(path, stat.S_IWRITE)
            path.rmdir()
        except OSError:
            if ignore_errors:
                stats.errors += 1
                return
            raise
    except OSError:
        if ignore_errors:
            stats.errors += 1
            return
        raise

    stats.dirs += 1


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


# delete_old_files内で同名のパラメーターと衝突するため別名を用意する
_delete_empty_dirs = delete_empty_dirs


def sync(src: str | pathlib.Path, dst: str | pathlib.Path, delete: bool = False) -> None:
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
            # 更新日時を比較し、ソースの方が新しければコピー
            if src.stat().st_mtime_ns != dst.stat().st_mtime_ns:
                logger.info(f"コピー: {src} -> {dst}")
                shutil.copy2(src, dst)
        else:
            # コピー先がファイルでない場合はいったん削除
            if dst.exists():
                if dst.is_dir():
                    logger.info(f"削除: {dst}")
                    rmtree(dst)
                else:
                    logger.info(f"削除: {dst}")
                    dst.unlink()
            dst.parent.mkdir(parents=True, exist_ok=True)
            # コピー
            logger.info(f"コピー: {src} -> {dst}")
            shutil.copy2(src, dst)
    elif src.is_dir():
        # コピー先がディレクトリでない場合はいったん削除
        if not dst.is_dir():
            if dst.exists():
                logger.info(f"削除: {dst}")
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
                        rmtree(dst_child)
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
        if delete_empty_dirs:
            # delete_empty_dirs関数に委譲（keep_root_empty_dirに応じてpath自体の
            # 削除可否が切り替わる）。引数名の衝突のため別名で呼び出す。
            _delete_empty_dirs(path, keep_root=keep_root_empty_dir)
