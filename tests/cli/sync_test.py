"""ディレクトリ同期のコピーと削除をCLIから実行する。"""

import os
from pathlib import Path

from pytilpack.cli.main import main


def test_sync_cli(tmp_path: Path) -> None:
    """コピー元の内容を反映し、削除指定時だけコピー先の余剰を除く。"""
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    (source / "file.txt").write_text("新しい内容", encoding="utf-8")
    (target / "file.txt").write_text("古い内容", encoding="utf-8")
    os.utime(target / "file.txt", (1, 1))
    extra = target / "extra.txt"
    extra.write_text("余剰", encoding="utf-8")
    main(["sync", str(source), str(target)])
    assert (target / "file.txt").read_text(encoding="utf-8") == "新しい内容"
    assert extra.exists()
    main(["sync", str(source), str(target), "--delete"])
    assert not extra.exists()
    assert (target / "file.txt").read_text(encoding="utf-8") == "新しい内容"
