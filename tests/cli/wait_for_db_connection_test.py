"""wait_for_db_connection.pyのテスト。"""

import pytest

import pytilpack.cli.wait_for_db_connection


@pytest.mark.parametrize(
    "url,expected",
    [
        ("postgresql://user:pass@localhost/db", False),
        ("postgresql+psycopg2://user:pass@localhost/db", False),
        ("mysql://user:pass@localhost/db", False),
        ("sqlite:///path/to/db.sqlite", False),
        ("postgresql+asyncpg://user:pass@localhost/db", True),
        ("sqlite+aiosqlite:///path/to/db.sqlite", True),
        ("mysql+aiomysql://user:pass@localhost/db", True),
        ("mysql+asyncmy://user:pass@localhost/db", True),
        ("postgresql+aiopg://user:pass@localhost/db", True),
    ],
)
def test_is_async_url(url: str, expected: bool) -> None:
    """is_async_urlのテスト。"""
    assert pytilpack.cli.wait_for_db_connection.is_async_url(url) == expected
