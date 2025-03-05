"""テストコード。"""

import datetime

import pytest
import sqlalchemy
import sqlalchemy.orm

import pytilpack.sqlalchemy_


class Base(sqlalchemy.orm.DeclarativeBase):  # type: ignore[name-defined]
    """ベースクラス。"""

    __test__ = False


class Test1(Base, pytilpack.sqlalchemy_.Mixin):
    """テストクラス。"""

    __test__ = False
    __tablename__ = "test"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)


class Test2(Base, pytilpack.sqlalchemy_.Mixin):
    """テストクラス。"""

    __test__ = False
    __tablename__ = "test2"
    __table_args__ = (sqlalchemy.UniqueConstraint("value1", "value2", name="uc1"),)

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(
        sqlalchemy.String(250), nullable=False, unique=True, doc="名前"
    )
    pass_hash = sqlalchemy.Column(
        sqlalchemy.String(100), default=None, comment="パスハッシュ"
    )
    # 有効フラグ
    enabled = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=True)
    is_admin = sqlalchemy.Column(  # このコメントは無視されてほしい
        sqlalchemy.Boolean, nullable=False, default=False
    )
    value1 = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, default=0)
    value2 = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, default=512)
    value3 = sqlalchemy.Column(sqlalchemy.Float, nullable=False, default=1.0)
    value4 = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
    value5 = sqlalchemy.Column(sqlalchemy.Text, nullable=False, default=lambda: "func")


@pytest.fixture(name="engine", scope="module", autouse=True)
def _engine():
    """DB接続。"""
    engine = sqlalchemy.create_engine("sqlite:///:memory:")
    pytilpack.sqlalchemy_.register_ping()
    yield engine


@pytest.fixture(name="session", scope="module")
def _session(engine: sqlalchemy.engine.Engine):
    """セッション。"""
    yield sqlalchemy.orm.Session(engine)


def test_get_by_id(session: sqlalchemy.orm.Session) -> None:
    Test1.query = session.query(Test1)  # 仮

    Base.metadata.create_all(session.bind)  # type: ignore
    session.add(Test1(id=1))
    session.commit()

    assert Test1.get_by_id(1).id == 1  # type: ignore
    assert Test1.get_by_id(2) is None
    assert Test1.get_by_id(1, for_update=True).id == 1  # type: ignore


def test_to_dict() -> None:
    test2 = Test2(name="test2", enabled=True, value4=datetime.datetime(2021, 1, 1))
    assert test2.to_dict(excludes=["pass_hash"]) == {
        "id": None,
        "name": "test2",
        "enabled": True,
        "is_admin": None,
        "value1": None,
        "value2": None,
        "value3": None,
        "value4": datetime.datetime(2021, 1, 1),
        "value5": None,
    }
    assert test2.to_dict(includes=["name", "value3"], exclude_none=True) == {
        "name": "test2"
    }


def test_describe() -> None:
    """describe()のテスト。"""
    desc = pytilpack.sqlalchemy_.describe(Base)
    print(f"{'=' * 64}")
    print(desc)
    print(f"{'=' * 64}")
    assert (
        desc
        == """\
Table: test
+---------+---------+--------+-------+-----------+----------------+-----------+
| Field   | Type    | Null   | Key   | Default   | Extra          | Comment   |
+=========+=========+========+=======+===========+================+===========+
| id      | INTEGER | NO     | PRI   | NULL      | auto_increment |           |
+---------+---------+--------+-------+-----------+----------------+-----------+

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
| value3    | FLOAT        | NO     |       | 1.0        |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| value4    | DATETIME     | NO     |       | NULL       |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| value5    | TEXT         | NO     |       | (function) |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
"""
    )
