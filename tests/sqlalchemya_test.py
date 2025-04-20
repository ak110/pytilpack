"""テストコード。"""

import datetime

import pytest
import sqlalchemy
import sqlalchemy.exc
import sqlalchemy.ext.asyncio
import sqlalchemy.orm

import pytilpack.sqlalchemy_


class Base(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy_.AsyncMixin):
    """ベースクラス。"""


class Test1(Base, pytilpack.sqlalchemy_.AsyncUniqueIDMixin):
    """テストクラス。"""

    __test__ = False
    __tablename__ = "test"

    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(primary_key=True)
    unique_id: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(
        sqlalchemy.String(43), unique=True, nullable=True, doc="ユニークID"
    )


class Test2(Base):
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
async def _engine():
    """DB接続。"""
    Base.init("sqlite+aiosqlite:///:memory:")
    yield Base.engine


@pytest.fixture(name="session", scope="module")
async def _session(engine: sqlalchemy.ext.asyncio.AsyncEngine):
    """セッション。"""
    del engine  # noqa
    async with Base.session_scope() as session:
        yield session


@pytest.mark.asyncio
async def test_get_by_id(session: sqlalchemy.ext.asyncio.AsyncSession) -> None:
    """get_by_idのテスト。"""
    async with Base.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session.add(Test1(id=1))
    await session.commit()

    assert (await Test1.get_by_id(1)).id == 1  # type: ignore
    assert (await Test1.get_by_id(2)) is None
    assert (await Test1.get_by_id(1, for_update=True)).id == 1  # type: ignore


@pytest.mark.asyncio
async def test_get_by_unique_id(session: sqlalchemy.ext.asyncio.AsyncSession) -> None:
    """get_by_unique_idのテスト。"""
    async with Base.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)
    test1 = Test1(id=2, unique_id=Test1.generate_unique_id())
    assert test1.unique_id is not None and len(test1.unique_id) == 43
    unique_id = test1.unique_id
    session.add(test1)
    await session.commit()

    assert (await Test1.get_by_unique_id(unique_id)).id == 2  # type: ignore
    assert (await Test1.get_by_unique_id(unique_id, allow_id=True)).id == 2  # type: ignore
    assert (await Test1.get_by_unique_id(2)) is None
    assert (await Test1.get_by_unique_id(2, allow_id=True)).id == 2  # type: ignore
    assert (await Test1.get_by_unique_id("2", allow_id=True)) is None


def test_to_dict() -> None:
    """to_dictのテスト。"""
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
| value3    | FLOAT        | NO     |       | 1.0        |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| value4    | DATETIME     | NO     |       | NULL       |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| value5    | TEXT         | NO     |       | (function) |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
"""
    )


@pytest.mark.asyncio
async def test_await_for_connection() -> None:
    """await_for_connectionのテスト。"""
    # 正常系
    await pytilpack.sqlalchemy_.await_for_connection(
        "sqlite+aiosqlite:///:memory:", timeout=1.0
    )

    # 異常系: タイムアウト
    with pytest.raises(sqlalchemy.exc.OperationalError):
        await pytilpack.sqlalchemy_.await_for_connection(
            "sqlite+aiosqlite:////nonexistent/path/db.sqlite3", timeout=1.0
        )


@pytest.mark.asyncio
async def test_asafe_close() -> None:
    """asafe_closeのテスト。"""
    engine = sqlalchemy.ext.asyncio.create_async_engine("sqlite+aiosqlite:///:memory:")
    session = sqlalchemy.ext.asyncio.AsyncSession(engine)
    await pytilpack.sqlalchemy_.asafe_close(session)  # 正常ケース

    # エラーケース（既にクローズ済み）
    await session.close()
    await pytilpack.sqlalchemy_.asafe_close(session)
    await pytilpack.sqlalchemy_.asafe_close(session, log_level=None)
