"""DB接続待機CLIの入口テスト。"""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("driver", ["sqlite", "sqlite+aiosqlite"])
def test_wait_for_db_connection_cli(tmp_path: Path, driver: str) -> None:
    """同期・非同期のSQLite接続成否をCLI終了コードで確認する。"""
    for should_connect in (True, False):
        database = tmp_path / "database.sqlite" if should_connect else tmp_path / "missing" / "database.sqlite"
        url = f"{driver}:///{database}"
        result = subprocess.run(
            [sys.executable, "-m", "pytilpack.cli.main", "wait-for-db-connection", url, "--timeout", "0"],
            capture_output=True,
            text=True,
            check=False,
        )
        if should_connect:
            assert result.returncode == 0, result.stderr
        else:
            assert result.returncode != 0
            assert "DB接続タイムアウト" in result.stderr
