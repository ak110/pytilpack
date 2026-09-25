"""DB接続待機CLIの入口テスト。"""

import subprocess
import sys
from pathlib import Path

import pytest

import pytilpack.cli.main
import pytilpack.sqlalchemy


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


@pytest.mark.parametrize(
    ("url", "expected_mode"),
    [
        ("postgresql://user:pass@localhost/db", "sync"),
        ("postgresql+psycopg2://user:pass@localhost/db", "sync"),
        ("mysql://user:pass@localhost/db", "sync"),
        ("sqlite:///path/to/db.sqlite", "sync"),
        ("postgresql+asyncpg://user:pass@localhost/db", "async"),
        ("sqlite+aiosqlite:///path/to/db.sqlite", "async"),
        ("mysql+aiomysql://user:pass@localhost/db", "async"),
        ("mysql+asyncmy://user:pass@localhost/db", "async"),
        ("postgresql+aiopg://user:pass@localhost/db", "async"),
    ],
)
def test_wait_for_db_connection_cli_dispatch(monkeypatch: pytest.MonkeyPatch, url: str, expected_mode: str) -> None:
    """CLIがDB URLのドライバーに対応する接続経路を選ぶ。"""
    calls: list[tuple[str, str, float]] = []

    def fake_sync(value: str, timeout: float, **_kwargs: object) -> None:
        calls.append(("sync", value, timeout))

    async def fake_async(value: str, timeout: float, **_kwargs: object) -> None:
        calls.append(("async", value, timeout))

    monkeypatch.setattr(pytilpack.sqlalchemy, "wait_for_connection", fake_sync)
    monkeypatch.setattr(pytilpack.sqlalchemy, "await_for_connection", fake_async)
    pytilpack.cli.main.main(["wait-for-db-connection", url, "--timeout", "0"])
    assert calls == [(expected_mode, url, 0.0)]
