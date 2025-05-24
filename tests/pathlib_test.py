"""テストコード。"""

import datetime
import os
import pathlib
import shutil
import time

import pytilpack.pathlib_


def test_delete_file(tmp_path: pathlib.Path) -> None:
    """delete_file()のテスト。"""
    path = tmp_path / "test.txt"
    path.write_text("test")
    pytilpack.pathlib_.delete_file(path)
    assert not path.exists()


def test_get_size(tmp_path: pathlib.Path) -> None:
    """get_size()のテスト。"""
    (tmp_path / "test").mkdir()
    (tmp_path / "test" / "test.txt").write_text("test")
    assert pytilpack.pathlib_.get_size(tmp_path) == 4
    assert pytilpack.pathlib_.get_size(tmp_path / "not_exist") == 0


def test_delete_empty_dirs(tmp_path: pathlib.Path) -> None:
    """delete_empty_dirs()のテスト。"""
    # テスト用のディレクトリ階層を作成
    (tmp_path / "empty1").mkdir()
    (tmp_path / "empty2").mkdir()
    (tmp_path / "not_empty").mkdir()
    (tmp_path / "not_empty" / "file.txt").write_text("test")
    (tmp_path / "nested" / "empty").mkdir(parents=True)

    # keep_root=Trueの場合（デフォルト）
    pytilpack.pathlib_.delete_empty_dirs(tmp_path)
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
    pytilpack.pathlib_.delete_empty_dirs(test_dir, keep_root=False)
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
    pytilpack.pathlib_.sync(src, dst)
    assert (dst / "test.txt").exists()
    assert (dst / "test.txt").read_text() == "test1"

    # ファイルの更新テスト
    time.sleep(0.1)  # 時間差をつけるためにスリープ
    src_file.write_text("test2")
    pytilpack.pathlib_.sync(src, dst)
    assert (dst / "test.txt").read_text() == "test2"

    # サブディレクトリのテスト
    (src / "subdir").mkdir()
    (src / "subdir" / "test2.txt").write_text("test3")
    pytilpack.pathlib_.sync(src, dst)
    assert (dst / "subdir").is_dir()
    assert (dst / "subdir" / "test2.txt").read_text() == "test3"

    # ファイル→ディレクトリの変更テスト
    file_to_dir = src / "file_to_dir"
    file_to_dir.write_text("test4")
    pytilpack.pathlib_.sync(src, dst)
    assert (dst / "file_to_dir").is_file()
    file_to_dir.unlink()
    file_to_dir.mkdir()
    (file_to_dir / "test.txt").write_text("test5")
    pytilpack.pathlib_.sync(src, dst)
    assert (dst / "file_to_dir").is_dir()
    assert (dst / "file_to_dir" / "test.txt").read_text() == "test5"

    # ディレクトリ→ファイルの変更テスト
    dir_to_file = src / "dir_to_file"
    dir_to_file.mkdir()
    (dir_to_file / "test.txt").write_text("test6")
    pytilpack.pathlib_.sync(src, dst)
    assert (dst / "dir_to_file").is_dir()
    shutil.rmtree(dir_to_file)
    dir_to_file.write_text("test7")
    pytilpack.pathlib_.sync(src, dst)
    assert (dst / "dir_to_file").is_file()
    assert (dst / "dir_to_file").read_text() == "test7"

    # deleteオプションのテスト
    (dst / "extra.txt").write_text("extra")
    (dst / "extra_dir").mkdir()
    (dst / "extra_dir" / "test.txt").write_text("extra")
    pytilpack.pathlib_.sync(src, dst, delete=True)
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
    pytilpack.pathlib_.delete_old_files(tmp_path, before)

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

    pytilpack.pathlib_.delete_old_files(test_dir, before, keep_root_empty_dir=False)
    assert not test_dir.exists()
