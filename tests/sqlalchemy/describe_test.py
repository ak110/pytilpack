"""SQLの構造表示を同期・非同期・Flaskのモデルで検証する。"""

import pytest
import sqlalchemy.orm

import pytilpack.sqlalchemy
from tests.sqlalchemy import async_test, flask_test, sync_test

_EXPECTED = """\
Table: test
+-----------+-------------+--------+-------+-----------+----------------+------------+
| Field     | Type        | Null   | Key   | Default   | Extra          | Comment    |
+===========+=============+========+=======+===========+================+============+
| id        | INTEGER     | NO     | PRI   | NULL      | auto_increment |            |
+-----------+-------------+--------+-------+-----------+----------------+------------+
| unique_id | VARCHAR(43) | YES    | UNI   | NULL      |                | ユニークID |
+-----------+-------------+--------+-------+-----------+----------------+------------+

Table: test2
+-----------+--------------+--------+-------+------------+----------------+--------------+
| Field     | Type         | Null   | Key   | Default    | Extra          | Comment      |
+===========+==============+========+=======+============+================+==============+
| id        | INTEGER      | NO     | PRI   | NULL       | auto_increment |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| name      | VARCHAR(250) | NO     | UNI   | NULL       |                | 名前         |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| pass_hash | VARCHAR(100) | YES    |       | NULL       |                | パスハッシュ |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| enabled   | BOOLEAN      | NO     |       | True       |                | 有効フラグ   |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| is_admin  | BOOLEAN      | NO     |       | False      |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| value1    | INTEGER      | YES    |       | 0          |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| value2    | INTEGER      | NO     |       | 512        |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| value0    | FLOAT        | NO     |       | 1.0        |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| value4    | DATETIME     | NO     |       | NULL       |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| value5    | TEXT         | NO     |       | (function) |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
"""


@pytest.mark.parametrize(
    ("base", "synchronous"),
    [(sync_test.Base, True), (async_test.Base, False), (flask_test.Base, False)],
    ids=["sync", "async", "flask"],
)
def test_describe(base: type[sqlalchemy.orm.DeclarativeBase], synchronous: bool) -> None:
    """既存の3モデル構成の期待値を保って構造表示を確認する。"""
    expected = _EXPECTED
    if synchronous:
        first = _EXPECTED.split("\n\n", 1)[0]
        expected = (
            _EXPECTED.replace("Table: test\n", "Table: test1\n")
            + "\n"
            + first.replace("Table: test\n", "Table: test3\n")
            + "\n"
        )
    assert pytilpack.sqlalchemy.describe(base) == expected
