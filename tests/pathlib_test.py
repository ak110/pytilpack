import datetime as dt
import functools
import os
import pathlib
import shutil
import sys
import time
import typing

import pytest

import pytilpack.pathlib


def test_delete_file(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "test.txt"
    path.write_text("test")
    pytilpack.pathlib.delete_file(path)
    assert not path.exists()


def test_rmtree_readonly_file(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = tmp_path / "dir"
    d.mkdir()
    f = d / "readonly.txt"
    f.write_text("test")
    f.chmod(0o444)
    original_unlink = pathlib.Path.unlink
    attempts = 0

    def unlink(path: pathlib.Path, *args: typing.Any, **kwargs: typing.Any) -> None:
        nonlocal attempts
        if path == f:
            attempts += 1
            if attempts == 1:
                raise PermissionError("読み取り専用ファイル")
            assert path.stat().st_mode & 0o200
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "unlink", unlink)
    result = pytilpack.pathlib.rmtree(d)
    assert attempts == 2
    assert not d.exists()
    assert result.files == 1
    assert result.dirs == 1
    assert result.total_size == 4
    assert result.errors == 0


def test_rmtree_nonexistent(tmp_path: pathlib.Path) -> None:
    result = pytilpack.pathlib.rmtree(tmp_path / "nonexistent")
    assert result == pytilpack.pathlib.RmtreeResult(0, 0, 0, 0)


def test_rmtree_single_file(tmp_path: pathlib.Path) -> None:
    f = tmp_path / "single.txt"
    f.write_text("hello")
    result = pytilpack.pathlib.rmtree(f)
    assert not f.exists()
    assert result.files == 1
    assert result.dirs == 0
    assert result.total_size == 5
    assert result.errors == 0


def test_rmtree_empty_dir(tmp_path: pathlib.Path) -> None:
    d = tmp_path / "empty"
    d.mkdir()
    result = pytilpack.pathlib.rmtree(d)
    assert not d.exists()
    assert result.files == 0
    assert result.dirs == 1
    assert result.total_size == 0
    assert result.errors == 0


def test_rmtree_nested(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    sub = root / "sub"
    sub.mkdir()
    (root / "a.txt").write_text("abc")
    (sub / "b.txt").write_text("12345")

    result = pytilpack.pathlib.rmtree(root)
    assert not root.exists()
    assert result.files == 2
    assert result.dirs == 2
    assert result.total_size == 8
    assert result.errors == 0


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX固有のパーミッション制御を利用するため")
def test_rmtree_ignore_errors_with_unreadable_subdir(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    locked = root / "locked"
    locked.mkdir()
    (locked / "inner.txt").write_text("x")
    locked.chmod(0o000)
    try:
        result = pytilpack.pathlib.rmtree(root, ignore_errors=True)
        assert result.errors >= 1
    finally:
        locked.chmod(0o700)
        if root.exists():
            shutil.rmtree(root)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX固有のsymlink挙動に依存するため")
def test_rmtree_symlink_to_dir(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(NotADirectoryError):
        pytilpack.pathlib.rmtree(link)
    assert target.exists()
    assert link.is_symlink()


def test_rmtree_result_add() -> None:
    r1 = pytilpack.pathlib.RmtreeResult(files=1, dirs=2, total_size=10, errors=0)
    r2 = pytilpack.pathlib.RmtreeResult(files=3, dirs=4, total_size=20, errors=1)
    expected = pytilpack.pathlib.RmtreeResult(files=4, dirs=6, total_size=30, errors=1)
    assert r1 + r2 == expected
    assert sum([r1, r2]) == expected
    bad: typing.Any = 1
    with pytest.raises(TypeError):
        _ = r1 + bad


def test_get_size(tmp_path: pathlib.Path) -> None:
    (tmp_path / "test").mkdir()
    (tmp_path / "test" / "test.txt").write_text("test")
    assert pytilpack.pathlib.get_size(tmp_path) == 4
    assert pytilpack.pathlib.get_size(tmp_path / "not_exist") == 0


def test_delete_empty_dirs(tmp_path: pathlib.Path) -> None:
    (tmp_path / "empty1").mkdir()
    (tmp_path / "empty2").mkdir()
    (tmp_path / "not_empty").mkdir()
    (tmp_path / "not_empty" / "file.txt").write_text("test")
    (tmp_path / "nested" / "empty").mkdir(parents=True)

    pytilpack.pathlib.delete_empty_dirs(tmp_path)
    assert not (tmp_path / "empty1").exists()
    assert not (tmp_path / "empty2").exists()
    assert (tmp_path / "not_empty").exists()
    assert (tmp_path / "not_empty" / "file.txt").exists()
    assert not (tmp_path / "nested" / "empty").exists()
    assert not (tmp_path / "nested").exists()
    assert tmp_path.exists()

    test_dir = tmp_path / "test_no_keep"
    test_dir.mkdir()
    (test_dir / "empty").mkdir()

    pytilpack.pathlib.delete_empty_dirs(test_dir, keep_root=False)
    assert not test_dir.exists()


@pytest.mark.parametrize("top_link", [False, True])
@pytest.mark.parametrize("keep_root", [False, True])
def test_delete_empty_dirs_preserve_external(tmp_path: pathlib.Path, top_link: bool, keep_root: bool) -> None:
    target = tmp_path / "outside"
    empty = target / "empty"
    empty.mkdir(parents=True)
    root = tmp_path / "root"
    root.mkdir()
    link = root / "link"
    link.symlink_to(target, target_is_directory=True)

    pytilpack.pathlib.delete_empty_dirs(link if top_link else root, keep_root=keep_root)

    assert empty.is_dir()
    assert link.is_symlink()
    assert root.is_dir()


@pytest.mark.parametrize(
    "operation",
    [
        functools.partial(pytilpack.pathlib.delete_empty_dirs, keep_root=False),
        functools.partial(
            pytilpack.pathlib.delete_old_files,
            before=dt.datetime(2100, 1, 1),
            keep_root_empty_dir=False,
        ),
    ],
    ids=["empty", "old"],
)
def test_deletion_directory_links(tmp_path: pathlib.Path, operation: typing.Callable[[pathlib.Path], None]) -> None:
    root = tmp_path / "root"
    internal = root / "internal"
    internal.mkdir(parents=True)
    link = root / "link"
    link.symlink_to(internal, target_is_directory=True)
    cycle = root / "cycle"
    cycle.symlink_to(root, target_is_directory=True)

    operation(root)

    assert link.is_symlink()
    assert cycle.is_symlink()
    assert root.is_dir()
    assert not internal.exists()


def test_sync(tmp_path: pathlib.Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()

    src_file = src / "test.txt"
    src_file.write_text("test1")
    pytilpack.pathlib.sync(src, dst)
    assert (dst / "test.txt").exists()
    assert (dst / "test.txt").read_text() == "test1"

    copied_mtime_ns = (dst / "test.txt").stat().st_mtime_ns
    src_file.write_text("test2")
    os.utime(src_file, ns=(src_file.stat().st_atime_ns, copied_mtime_ns + 1_000_000_000))
    pytilpack.pathlib.sync(src, dst)
    assert (dst / "test.txt").read_text() == "test2"

    (src / "subdir").mkdir()
    (src / "subdir" / "test2.txt").write_text("test3")
    pytilpack.pathlib.sync(src, dst)
    assert (dst / "subdir").is_dir()
    assert (dst / "subdir" / "test2.txt").read_text() == "test3"

    file_to_dir = src / "file_to_dir"
    file_to_dir.write_text("test4")
    pytilpack.pathlib.sync(src, dst)
    assert (dst / "file_to_dir").is_file()
    file_to_dir.unlink()
    file_to_dir.mkdir()
    (file_to_dir / "test.txt").write_text("test5")
    pytilpack.pathlib.sync(src, dst)
    assert (dst / "file_to_dir").is_dir()
    assert (dst / "file_to_dir" / "test.txt").read_text() == "test5"

    dir_to_file = src / "dir_to_file"
    dir_to_file.mkdir()
    (dir_to_file / "test.txt").write_text("test6")
    pytilpack.pathlib.sync(src, dst)
    assert (dst / "dir_to_file").is_dir()
    shutil.rmtree(dir_to_file)
    dir_to_file.write_text("test7")
    pytilpack.pathlib.sync(src, dst)
    assert (dst / "dir_to_file").is_file()
    assert (dst / "dir_to_file").read_text() == "test7"

    (dst / "extra.txt").write_text("extra")
    (dst / "extra_dir").mkdir()
    (dst / "extra_dir" / "test.txt").write_text("extra")
    pytilpack.pathlib.sync(src, dst, delete=True)
    assert not (dst / "extra.txt").exists()
    assert not (dst / "extra_dir").exists()


def test_delete_old_files(tmp_path: pathlib.Path) -> None:
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir1" / "old.txt").write_text("old")
    (tmp_path / "dir2").mkdir()
    (tmp_path / "dir2" / "new.txt").write_text("new")
    (tmp_path / "empty").mkdir()

    old_time = dt.datetime.now() - dt.timedelta(days=2)
    old_path = tmp_path / "dir1" / "old.txt"
    os_time = time.mktime(old_time.timetuple())
    os.utime(old_path, (os_time, os_time))

    before = dt.datetime.now() - dt.timedelta(days=1)
    pytilpack.pathlib.delete_old_files(tmp_path, before)

    assert not (tmp_path / "dir1" / "old.txt").exists()
    assert not (tmp_path / "dir1").exists()
    assert (tmp_path / "dir2" / "new.txt").exists()
    assert (tmp_path / "dir2").exists()
    assert not (tmp_path / "empty").exists()
    assert tmp_path.exists()

    test_dir = tmp_path / "test_no_keep"
    test_dir.mkdir()
    old_file = test_dir / "old.txt"
    old_file.write_text("old")
    os.utime(old_file, (os_time, os_time))

    pytilpack.pathlib.delete_old_files(test_dir, before, keep_root_empty_dir=False)
    assert not test_dir.exists()


@pytest.mark.parametrize("top_link", [False, True])
@pytest.mark.parametrize("delete_empty_dirs", [False, True])
def test_delete_old_files_preserve_external(tmp_path: pathlib.Path, top_link: bool, delete_empty_dirs: bool) -> None:
    target = tmp_path / "outside"
    empty = target / "empty"
    empty.mkdir(parents=True)
    protected = target / "old.txt"
    protected.write_text("protected", encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    link = root / "link"
    link.symlink_to(target, target_is_directory=True)

    pytilpack.pathlib.delete_old_files(
        link if top_link else root,
        dt.datetime(2100, 1, 1),
        delete_empty_dirs=delete_empty_dirs,
        keep_root_empty_dir=False,
    )

    assert protected.read_text(encoding="utf-8") == "protected"
    assert empty.is_dir()
    assert link.is_symlink()
    assert root.is_dir()


def test_delete_old_files_file_symlink(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("protected", encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    link = root / "link.txt"
    link.symlink_to(target)

    pytilpack.pathlib.delete_old_files(root, dt.datetime(2100, 1, 1))

    assert not link.is_symlink()
    assert target.read_text(encoding="utf-8") == "protected"
