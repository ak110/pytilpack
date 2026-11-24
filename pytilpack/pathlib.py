__lazy_modules__ = ["dataclasses", "datetime", "logging", "os", "pathlib", "shutil", "stat", "typing"]

import dataclasses
import datetime as dt
import logging
import os
import pathlib
import shutil
import stat
import typing

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class RmtreeResult:
    files: int = 0
    dirs: int = 0
    total_size: int = 0
    errors: int = 0

    def __add__(self, other: "RmtreeResult") -> "RmtreeResult":
        if not isinstance(other, RmtreeResult):
            return NotImplemented
        return RmtreeResult(
            files=self.files + other.files,
            dirs=self.dirs + other.dirs,
            total_size=self.total_size + other.total_size,
            errors=self.errors + other.errors,
        )

    def __radd__(self, other: int) -> "RmtreeResult":
        if other == 0:
            return self
        return NotImplemented


@dataclasses.dataclass
class _RmtreeStats:
    files: int = 0
    dirs: int = 0
    total_size: int = 0
    errors: int = 0


def append_text(path: str | pathlib.Path, data: str, encoding: str = "utf-8", errors: str = "strict") -> None:
    path = pathlib.Path(path)
    with path.open("a", encoding=encoding, errors=errors) as f:
        f.write(data)


def append_bytes(path: str | pathlib.Path, data: bytes) -> None:
    path = pathlib.Path(path)
    with path.open("ab") as f:
        f.write(data)


def delete_file(path: str | pathlib.Path) -> None:
    path = pathlib.Path(path)
    if path.is_file():
        path.unlink()


def rmtree(path: str | pathlib.Path, ignore_errors: bool = False) -> RmtreeResult:
    path = pathlib.Path(path)
    stats = _RmtreeStats()

    if path.is_junction():
        raise NotADirectoryError(
            f"Cannot call rmtree on a directory junction: {path}. To remove the junction itself, use pathlib.Path.rmdir()."
        )
    if path.is_symlink():
        if path.is_dir():
            raise NotADirectoryError(
                f"Cannot call rmtree on a symbolic link: {path}. To remove the link itself, use pathlib.Path.unlink()."
            )
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

    dirs: list[pathlib.Path] = []
    for root, dirnames, filenames in path.walk(on_error=on_walk_error):
        for dname in [d for d in dirnames if (root / d).is_junction()]:
            dirnames.remove(dname)
            _remove_link(root / dname, stats, ignore_errors)
        for fname in filenames:
            _remove_file(root / fname, stats, ignore_errors)
        dirs.append(root)
    for root in reversed(dirs):
        _remove_dir(root, stats, ignore_errors)

    return _to_result(stats)


def _to_result(stats: _RmtreeStats) -> RmtreeResult:
    return RmtreeResult(files=stats.files, dirs=stats.dirs, total_size=stats.total_size, errors=stats.errors)


def _remove_file(path: pathlib.Path, stats: _RmtreeStats, ignore_errors: bool) -> None:
    is_link = path.is_symlink()
    try:
        size = 0 if is_link else path.stat().st_size
    except OSError:
        if ignore_errors:
            stats.errors += 1
            return
        raise

    if not _remove_with_retry(path.unlink, path, stats, ignore_errors):
        return

    stats.files += 1
    stats.total_size += size


def _remove_link(path: pathlib.Path, stats: _RmtreeStats, ignore_errors: bool) -> None:
    if _remove_with_retry(path.rmdir, path, stats, ignore_errors):
        stats.files += 1


def _remove_dir(path: pathlib.Path, stats: _RmtreeStats, ignore_errors: bool) -> None:
    if not _remove_with_retry(path.rmdir, path, stats, ignore_errors):
        return

    stats.dirs += 1


def _remove_with_retry(remove: typing.Callable[[], None], path: pathlib.Path, stats: _RmtreeStats, ignore_errors: bool) -> bool:
    try:
        remove()
    except PermissionError:
        try:
            if _is_link(path):
                raise
            os.chmod(path, stat.S_IWRITE)
            remove()
        except OSError:
            if ignore_errors:
                stats.errors += 1
                return False
            raise
    except OSError:
        if ignore_errors:
            stats.errors += 1
            return False
        raise
    return True


def get_size(path: str | pathlib.Path) -> int:
    try:
        path = pathlib.Path(path)
        if path.is_file():
            try:
                return path.stat().st_size
            except Exception:
                logger.warning(f"ファイルサイズ取得失敗: {path}。サイズを0として処理を続ける", exc_info=True)
                return 0
        elif path.is_dir():
            total_size: int = 0
            try:
                for child in path.iterdir():
                    total_size += get_size(child)
            except Exception:
                logger.warning(f"ディレクトリサイズ取得失敗: {path}。取得済みの分だけを合計して処理を続ける", exc_info=True)
            return total_size
        else:
            return 0
    except Exception:
        logger.warning(f"ファイル・ディレクトリサイズ取得失敗: {path}。サイズを0として処理を続ける", exc_info=True)
        return 0


def delete_empty_dirs(path: str | pathlib.Path, keep_root: bool = True) -> None:
    path = pathlib.Path(path)
    if path.is_symlink() or not path.is_dir():
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
        logger.warning(
            f"ディレクトリの削除に失敗: {path}。削除せずに処理を続ける。権限と使用中のプロセスを確かめる", exc_info=True
        )


_delete_empty_dirs = delete_empty_dirs


def sync(src: str | pathlib.Path, dst: str | pathlib.Path, delete: bool = False) -> None:
    src = pathlib.Path(src)
    dst = pathlib.Path(dst)

    if not src.exists():
        logger.warning(f"コピー元が存在しません: {src}。何もせずに終了した。コピー元のパスを見直す")
        return

    src_resolved = src.resolve()
    dst_resolved = dst.resolve()
    if src_resolved == dst_resolved:
        logger.info(f"コピー元とコピー先が同じため何もしない: {src}")
        return
    if src.is_dir() and dst_resolved.is_relative_to(src_resolved):
        raise ValueError(f"コピー先がコピー元の内側にあるため同期できない: {src} -> {dst}")
    if src_resolved.is_relative_to(dst_resolved):
        raise ValueError(f"コピー元がコピー先の内側にあるため、同期中にコピー元を置き換えるか削除しうる: {src} -> {dst}")

    _sync_entry(src, dst_resolved, delete)


def _is_link(path: pathlib.Path) -> bool:
    return path.is_symlink() or path.is_junction()


def _unlink_link(path: pathlib.Path) -> None:
    if path.is_junction():
        path.rmdir()
    else:
        path.unlink()


def _sync_entry(src: pathlib.Path, dst: pathlib.Path, delete: bool) -> None:
    if not src.exists():
        logger.warning(f"コピー元が存在しません: {src}。何もせずに終了した。コピー元のパスを見直す")
        return

    dst_is_link = _is_link(dst)

    if src.is_file():
        if not dst_is_link and dst.is_file():
            if src.stat().st_mtime_ns != dst.stat().st_mtime_ns:
                logger.info(f"コピー: {src} -> {dst}")
                shutil.copy2(src, dst)
            return
        if dst_is_link:
            logger.info(f"削除: {dst}")
            _unlink_link(dst)
        elif dst.is_dir():
            logger.info(f"削除: {dst}")
            rmtree(dst)
        elif dst.exists():
            logger.info(f"削除: {dst}")
            dst.unlink()
        dst.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"コピー: {src} -> {dst}")
        shutil.copy2(src, dst)
    elif src.is_dir():
        if dst_is_link:
            logger.info(f"削除: {dst}")
            _unlink_link(dst)
        elif dst.exists() and not dst.is_dir():
            logger.info(f"削除: {dst}")
            dst.unlink()
        if not dst.is_dir():
            logger.info(f"作成: {dst}")
            dst.mkdir(parents=True)

        for src_child in src.iterdir():
            _sync_entry(src_child, dst / src_child.name, delete)

        if delete:
            for dst_child in dst.iterdir():
                src_child = src / dst_child.name
                if not src_child.exists():
                    logger.info(f"削除: {dst_child}")
                    if _is_link(dst_child):
                        _unlink_link(dst_child)
                    elif dst_child.is_dir():
                        rmtree(dst_child)
                    else:
                        dst_child.unlink()


def delete_old_files(
    path: str | pathlib.Path,
    before: dt.datetime,
    delete_empty_dirs: bool = True,  # pylint: disable=redefined-outer-name
    keep_root_empty_dir: bool = True,
) -> None:
    path = pathlib.Path(path)
    if path.is_symlink() and path.is_dir():
        return
    if not path.exists():
        return

    if path.is_file():
        try:
            mtime = dt.datetime.fromtimestamp(path.stat().st_mtime)
            if mtime < before:
                logger.info(f"削除: {path}")
                path.unlink()
        except Exception:
            logger.warning(
                f"ファイルの削除に失敗: {path}。削除せずに処理を続ける。権限と使用中のプロセスを確かめる", exc_info=True
            )
    elif path.is_dir():
        for item in list(path.iterdir()):
            delete_old_files(item, before, delete_empty_dirs, keep_root_empty_dir=False)

        if delete_empty_dirs:
            _delete_empty_dirs(path, keep_root=keep_root_empty_dir)
