"""テストコード。"""

import datetime
import os
import pathlib
import shutil
import sys
import time
import typing

import pytest

import pytilpack.pathlib


def test_delete_file(tmp_path: pathlib.Path) -> None:
    """delete_file()のテスト。"""
    path = tmp_path / "test.txt"
    path.write_text("test")
    pytilpack.pathlib.delete_file(path)
    assert not path.exists()


def test_rmtree_readonly_file(tmp_path: pathlib.Path) -> None:
    """rmtree(): 読み取り専用ファイルを含むディレクトリの削除。"""
    d = tmp_path / "dir"
    d.mkdir()
    f = d / "readonly.txt"
    f.write_text("test")
    f.chmod(0o444)
    result = pytilpack.pathlib.rmtree(d)
    assert not d.exists()
    assert result.files == 1
    assert result.dirs == 1
    assert result.total_size == 4
    assert result.errors == 0


def test_rmtree_nonexistent(tmp_path: pathlib.Path) -> None:
    """rmtree(): 非存在パスは空の結果を返す。"""
    result = pytilpack.pathlib.rmtree(tmp_path / "nonexistent")
    assert result == pytilpack.pathlib.RmtreeResult(0, 0, 0, 0)


def test_rmtree_single_file(tmp_path: pathlib.Path) -> None:
    """rmtree(): 単一ファイルをトップに渡すケース。"""
    f = tmp_path / "single.txt"
    f.write_text("hello")  # 5 bytes
    result = pytilpack.pathlib.rmtree(f)
    assert not f.exists()
    assert result.files == 1
    assert result.dirs == 0
    assert result.total_size == 5
    assert result.errors == 0


def test_rmtree_empty_dir(tmp_path: pathlib.Path) -> None:
    """rmtree(): 空ディレクトリをトップに渡すケース。"""
    d = tmp_path / "empty"
    d.mkdir()
    result = pytilpack.pathlib.rmtree(d)
    assert not d.exists()
    assert result.files == 0
    assert result.dirs == 1
    assert result.total_size == 0
    assert result.errors == 0


def test_rmtree_nested(tmp_path: pathlib.Path) -> None:
    """rmtree(): ネスト構造（ルート1 + サブ1 + ファイル2）。"""
    root = tmp_path / "root"
    root.mkdir()
    sub = root / "sub"
    sub.mkdir()
    (root / "a.txt").write_text("abc")  # 3 bytes
    (sub / "b.txt").write_text("12345")  # 5 bytes

    result = pytilpack.pathlib.rmtree(root)
    assert not root.exists()
    assert result.files == 2
    assert result.dirs == 2
    assert result.total_size == 8
    assert result.errors == 0


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX固有のパーミッション制御を利用するため")
def test_rmtree_ignore_errors_with_unreadable_subdir(tmp_path: pathlib.Path) -> None:
    """rmtree(ignore_errors=True): アクセス不能なサブディレクトリを含むケース。"""
    root = tmp_path / "root"
    root.mkdir()
    locked = root / "locked"
    locked.mkdir()
    (locked / "inner.txt").write_text("x")
    # 走査・削除を阻害するため実行権限を除去する
    locked.chmod(0o000)
    try:
        result = pytilpack.pathlib.rmtree(root, ignore_errors=True)
        assert result.errors >= 1
    finally:
        # テスト失敗時にもtmp_pathを後片付けできるよう権限を戻す
        locked.chmod(0o700)
        if root.exists():
            shutil.rmtree(root)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX固有のsymlink挙動に依存するため")
def test_rmtree_symlink_to_dir(tmp_path: pathlib.Path) -> None:
    """rmtree(): ディレクトリへのシンボリックリンクはNotADirectoryErrorを送出する。"""
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(NotADirectoryError):
        pytilpack.pathlib.rmtree(link)
    # 解決先・シンボリックリンク自体ともに残存する
    assert target.exists()
    assert link.is_symlink()


def test_rmtree_result_add() -> None:
    """RmtreeResult.__add__とsum()による集計。"""
    r1 = pytilpack.pathlib.RmtreeResult(files=1, dirs=2, total_size=10, errors=0)
    r2 = pytilpack.pathlib.RmtreeResult(files=3, dirs=4, total_size=20, errors=1)
    expected = pytilpack.pathlib.RmtreeResult(files=4, dirs=6, total_size=30, errors=1)
    assert r1 + r2 == expected
    assert sum([r1, r2]) == expected
    bad: typing.Any = 1
    with pytest.raises(TypeError):
        _ = r1 + bad


def test_get_size(tmp_path: pathlib.Path) -> None:
    """get_size()のテスト。"""
    (tmp_path / "test").mkdir()
    (tmp_path / "test" / "test.txt").write_text("test")
    assert pytilpack.pathlib.get_size(tmp_path) == 4
    assert pytilpack.pathlib.get_size(tmp_path / "not_exist") == 0


def test_delete_empty_dirs(tmp_path: pathlib.Path) -> None:
    """delete_empty_dirs()のテスト。"""
    # テスト用のディレクトリ階層を作成
    (tmp_path / "empty1").mkdir()
    (tmp_path / "empty2").mkdir()
    (tmp_path / "not_empty").mkdir()
    (tmp_path / "not_empty" / "file.txt").write_text("test")
    (tmp_path / "nested" / "empty").mkdir(parents=True)

    # keep_root=Trueの場合（デフォルト）
    pytilpack.pathlib.delete_empty_dirs(tmp_path)
    assert not (tmp_path / "empty1").exists()
    assert not (tmp_path / "empty2").exists()
    assert (tmp_path / "not_empty").exists()
    assert (tmp_path / "not_empty" / "file.txt").exists()
    assert not (tmp_path / "nested" / "empty").exists()
    assert not (tmp_path / "nested").exists()
    assert tmp_path.exists()

    # keep_root=Falseの場合の準備
    test_dir = tmp_path / "test_no_keep"
    test_dir.mkdir()
    (test_dir / "empty").mkdir()

    # keep_root=Falseの場合
    pytilpack.pathlib.delete_empty_dirs(test_dir, keep_root=False)
    assert not test_dir.exists()


def test_sync(tmp_path: pathlib.Path) -> None:
    """sync()のテスト。"""
    # テスト用のディレクトリ構造を作成
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()

    # ファイルのコピーテスト
    src_file = src / "test.txt"
    src_file.write_text("test1")
    pytilpack.pathlib.sync(src, dst)
    assert (dst / "test.txt").exists()
    assert (dst / "test.txt").read_text() == "test1"

    # ファイルの更新テスト
    time.sleep(0.1)  # 時間差をつけるためにスリープ
    src_file.write_text("test2")
    pytilpack.pathlib.sync(src, dst)
    assert (dst / "test.txt").read_text() == "test2"

    # サブディレクトリのテスト
    (src / "subdir").mkdir()
    (src / "subdir" / "test2.txt").write_text("test3")
    pytilpack.pathlib.sync(src, dst)
    assert (dst / "subdir").is_dir()
    assert (dst / "subdir" / "test2.txt").read_text() == "test3"

    # ファイル→ディレクトリの変更テスト
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

    # ディレクトリ→ファイルの変更テスト
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

    # deleteオプションのテスト
    (dst / "extra.txt").write_text("extra")
    (dst / "extra_dir").mkdir()
    (dst / "extra_dir" / "test.txt").write_text("extra")
    pytilpack.pathlib.sync(src, dst, delete=True)
    assert not (dst / "extra.txt").exists()
    assert not (dst / "extra_dir").exists()


def test_delete_old_files(tmp_path: pathlib.Path) -> None:
    """delete_old_files()のテスト。"""
    # テスト用のディレクトリ階層とファイルを作成
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir1" / "old.txt").write_text("old")
    (tmp_path / "dir2").mkdir()
    (tmp_path / "dir2" / "new.txt").write_text("new")
    (tmp_path / "empty").mkdir()

    # 古いファイルを作成するため、ファイルのタイムスタンプを過去に設定
    old_time = datetime.datetime.now() - datetime.timedelta(days=2)
    old_path = tmp_path / "dir1" / "old.txt"
    os_time = time.mktime(old_time.timetuple())
    os.utime(old_path, (os_time, os_time))

    # 現在時刻より1日前を基準に削除
    before = datetime.datetime.now() - datetime.timedelta(days=1)
    pytilpack.pathlib.delete_old_files(tmp_path, before)

    # 古いファイルと空になったディレクトリが削除されていることを確認
    assert not (tmp_path / "dir1" / "old.txt").exists()
    assert not (tmp_path / "dir1").exists()
    assert (tmp_path / "dir2" / "new.txt").exists()
    assert (tmp_path / "dir2").exists()
    assert not (tmp_path / "empty").exists()
    assert tmp_path.exists()

    # keep_root_empty_dir=Falseのテスト
    test_dir = tmp_path / "test_no_keep"
    test_dir.mkdir()
    old_file = test_dir / "old.txt"
    old_file.write_text("old")
    os.utime(old_file, (os_time, os_time))

    pytilpack.pathlib.delete_old_files(test_dir, before, keep_root_empty_dir=False)
    assert not test_dir.exists()
