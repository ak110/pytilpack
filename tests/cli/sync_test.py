"""syncのテスト。"""

import pathlib
import subprocess


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
    subprocess.run(["pytilpack", "sync", str(src), str(dst)], check=True)

    # ファイルがコピーされていることを確認
    assert (dst / "test.txt").exists()
    assert (dst / "test.txt").read_text() == "test1"

    # 余分なファイルを作成
    (dst / "extra.txt").write_text("extra")

    # --delete付きで同期実行
    subprocess.run(
        ["pytilpack", "sync", "--delete", str(src), str(dst)],
        check=True,
    )

    # 余分なファイルが削除されていることを確認
    assert not (dst / "extra.txt").exists()
