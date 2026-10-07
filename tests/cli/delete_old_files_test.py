"""古いファイルの削除条件をCLIから指定する。"""

import os
import time
from pathlib import Path

from pytilpack.cli.main import main


def test_delete_old_files_cli(tmp_path: Path) -> None:
    """古いファイルだけを削除し、新しいファイルを保持する。"""
    old = tmp_path / "old.txt"
    new = tmp_path / "new.txt"
    old.write_text("古い", encoding="utf-8")
    new.write_text("新しい", encoding="utf-8")
    past = time.time() - 3 * 86400
    os.utime(old, (past, past))
    main(["delete-old-files", str(tmp_path), "--days", "2"])
    assert not old.exists()
    assert new.read_text(encoding="utf-8") == "新しい"
