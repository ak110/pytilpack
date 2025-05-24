"""CLIユーティリティのテスト。"""

import pathlib
import subprocess
import sys


def test_delete_empty_dirs(tmp_path: pathlib.Path) -> None:
    """delete_empty_dirsのテスト。"""
    # 空のディレクトリを作成
    empty_dir = tmp_path / "empty" / "empty2"
    empty_dir.mkdir(parents=True)

    # コマンド実行
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytilpack.cli.delete_empty_dirs",
            str(empty_dir.parent),
        ],
        check=True,
    )

    assert not empty_dir.exists()
    assert empty_dir.parent.exists()

    # --no-keep-root付きで実行
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytilpack.cli.delete_empty_dirs",
            "--no-keep-root",
            str(empty_dir.parent),
        ],
        check=True,
    )

    assert not empty_dir.parent.exists()


def test_delete_old_files(tmp_path: pathlib.Path) -> None:
    """delete_old_filesのテスト。"""
    # ファイルを作成
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")

    # 7日前より古いファイルを削除：削除されないはず
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytilpack.cli.delete_old_files",
            "--days=7",
            str(tmp_path),
        ],
        check=True,
    )

    # ファイルが残っていること
    assert test_file.exists()

    # 1日後より古いファイルを削除：削除される
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytilpack.cli.delete_old_files",
            "--days=-1",
            str(tmp_path),
        ],
        check=True,
    )

    # ファイルが削除されていること
    assert not test_file.exists()


def test_sync(tmp_path: pathlib.Path) -> None:
    """syncのテスト。"""
    # テスト用のディレクトリ構造を作成
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()

    # ソースにファイルを作成
    src_file = src / "test.txt"
    src_file.write_text("test1")

    # 同期実行
    subprocess.run(
        [sys.executable, "-m", "pytilpack.cli.sync", str(src), str(dst)], check=True
    )

    # ファイルがコピーされていることを確認
    assert (dst / "test.txt").exists()
    assert (dst / "test.txt").read_text() == "test1"

    # 余分なファイルを作成
    (dst / "extra.txt").write_text("extra")

    # --delete付きで同期実行
    subprocess.run(
        [sys.executable, "-m", "pytilpack.cli.sync", "--delete", str(src), str(dst)],
        check=True,
    )

    # 余分なファイルが削除されていることを確認
    assert not (dst / "extra.txt").exists()
