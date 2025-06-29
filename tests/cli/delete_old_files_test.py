"""delete_old_filesのテスト。"""

import pathlib
import subprocess


def test_delete_old_files(tmp_path: pathlib.Path) -> None:
    """delete_old_filesのテスト。"""
    # ファイルを作成
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")

    # 7日前より古いファイルを削除：削除されないはず
    subprocess.run(
        [
            "pytilpack",
            "delete-old-files",
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
            "pytilpack",
            "delete-old-files",
            "--days=-1",
            str(tmp_path),
        ],
        check=True,
    )

    # ファイルが削除されていること
    assert not test_file.exists()
