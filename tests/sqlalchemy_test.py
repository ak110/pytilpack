"""テストコード。"""

import pytest
import sqlalchemy

import pytilpack.sqlalchemy_


class Base(sqlalchemy.orm.DeclarativeBase):
    """ベースクラス。"""

    __test__ = False


class Test1(Base, pytilpack.sqlalchemy_.IDMixin):
    """テストクラス。"""

    __test__ = False
    __tablename__ = "test"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)


class Test2(Base):
    """テストクラス。"""

    __test__ = False
    __tablename__ = "test2"
    __table_args__ = (sqlalchemy.UniqueConstraint("value1", "value2", name="uc1"),)

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String(250), nullable=False, unique=True)
    pass_hash = sqlalchemy.Column(sqlalchemy.String(100), default=None)
    enabled = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=True)
    is_admin = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)
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


def test_id_mixin(session: sqlalchemy.orm.Session) -> None:
    """register_ping()のテスト。"""

    Test1.query = session.query(Test1)  # 仮

    Base.metadata.create_all(session.bind)  # type: ignore
    session.add(Test1(id=1))
    session.commit()

    assert Test1.get_by_id(1).id == 1  # type: ignore
    assert Test1.get_by_id(2) is None
    assert Test1.get_by_id(1, for_update=True).id == 1  # type: ignore


def test_describe() -> None:
    """describe()のテスト。"""
    assert (
        pytilpack.sqlalchemy_.describe(Base.metadata)
        == """\
Table: test
+---------+---------+--------+-------+-----------+----------------+
| Field   | Type    | Null   | Key   | Default   | Extra          |
+=========+=========+========+=======+===========+================+
| id      | INTEGER | NO     | PRI   | NULL      | auto_increment |
+---------+---------+--------+-------+-----------+----------------+

Table: test2
+-----------+--------------+--------+-------+------------+----------------+
| Field     | Type         | Null   | Key   | Default    | Extra          |
+===========+==============+========+=======+============+================+
| id        | INTEGER      | NO     | PRI   | NULL       | auto_increment |
+-----------+--------------+--------+-------+------------+----------------+
| name      | VARCHAR(250) | NO     | UNI   | NULL       |                |
+-----------+--------------+--------+-------+------------+----------------+
| pass_hash | VARCHAR(100) | YES    |       | NULL       |                |
+-----------+--------------+--------+-------+------------+----------------+
| enabled   | BOOLEAN      | NO     |       | True       |                |
+-----------+--------------+--------+-------+------------+----------------+
| is_admin  | BOOLEAN      | NO     |       | False      |                |
+-----------+--------------+--------+-------+------------+----------------+
| value1    | INTEGER      | YES    |       | 0          |                |
+-----------+--------------+--------+-------+------------+----------------+
| value2    | INTEGER      | NO     |       | 512        |                |
+-----------+--------------+--------+-------+------------+----------------+
| value3    | FLOAT        | NO     |       | 1.0        |                |
+-----------+--------------+--------+-------+------------+----------------+
| value4    | DATETIME     | NO     |       | NULL       |                |
+-----------+--------------+--------+-------+------------+----------------+
| value5    | TEXT         | NO     |       | (function) |                |
+-----------+--------------+--------+-------+------------+----------------+
"""
    )
