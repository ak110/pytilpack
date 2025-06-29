"""delete_empty_dirsのテスト。"""

import pathlib
import subprocess


def test_delete_empty_dirs(tmp_path: pathlib.Path) -> None:
    """delete_empty_dirsのテスト。"""
    # 空のディレクトリを作成
    empty_dir = tmp_path / "empty" / "empty2"
    empty_dir.mkdir(parents=True)

    # コマンド実行
    subprocess.run(
        [
            "pytilpack",
            "delete-empty-dirs",
            str(empty_dir.parent),
        ],
        check=True,
    )

    assert not empty_dir.exists()
    assert empty_dir.parent.exists()

    # --no-keep-root付きで実行
    subprocess.run(
        [
            "pytilpack",
            "delete-empty-dirs",
            "--no-keep-root",
            str(empty_dir.parent),
        ],
        check=True,
    )

    assert not empty_dir.parent.exists()
