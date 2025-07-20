"""async版のテストコード。"""

import datetime
import typing

import pytest
import pytest_asyncio
import sqlalchemy
import sqlalchemy.exc
import sqlalchemy.ext.asyncio
import sqlalchemy.orm

import pytilpack.sqlalchemy


class Base(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy.AsyncMixin):
    """ベースクラス。"""


class Test1(Base, pytilpack.sqlalchemy.AsyncUniqueIDMixin):
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
    name = sqlalchemy.Column(sqlalchemy.String(250), nullable=False, unique=True, doc="名前")
    pass_hash = sqlalchemy.Column(sqlalchemy.String(100), default=None, comment="パスハッシュ")
    # 有効フラグ
    enabled = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=True)
    is_admin = sqlalchemy.Column(  # このコメントは無視されてほしい
        sqlalchemy.Boolean, nullable=False, default=False
    )
    value1 = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, default=0)
    value2 = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, default=512)
    value3 = sqlalchemy.Column("value0", sqlalchemy.Float, nullable=False, default=1.0)
    value4 = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
    value5 = sqlalchemy.Column(sqlalchemy.Text, nullable=False, default=lambda: "func")


@pytest_asyncio.fixture(name="engine", scope="module", autouse=True)
async def _engine() -> typing.AsyncGenerator[sqlalchemy.ext.asyncio.AsyncEngine, None]:
    """DB接続。"""
    Base.init("sqlite+aiosqlite:///:memory:")
    assert Base.engine is not None
    yield Base.engine


@pytest_asyncio.fixture(name="session", scope="module")
async def _session() -> typing.AsyncGenerator[sqlalchemy.ext.asyncio.AsyncSession, None]:
    """セッション。"""
    async with Base.session_scope() as session:
        yield session


@pytest.mark.asyncio
async def test_mixin_basic_functionality() -> None:
    """AsyncMixinの基本機能をテスト。"""
    # テーブル作成
    async with Base.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # セッションスコープのテスト
    async with Base.session_scope():
        # 件数取得 (0件)
        assert await Base.count(Test1.select()) == 0

        # データ挿入
        test_record = Test1(unique_id="test_name")
        Base.session().add(test_record)
        await Base.session().commit()

        # データ取得
        result = await Test1.get_by_id(test_record.id)
        assert result is not None
        assert result.unique_id == "test_name"

        # 件数取得 (1件)
        assert await Base.count(Test1.select()) == 1

        # 削除
        await Base.session().execute(Test1.delete())
        await Base.session().commit()

        # 件数取得 (0件)
        assert await Base.count(Test1.select()) == 0


@pytest.mark.asyncio
async def test_async_mixin_context_vars() -> None:
    """AsyncMixinのcontextvar管理をテスト。"""
    # テーブル作成
    async with Base.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # start_session / close_sessionのテスト
    token = await Base.start_session()
    try:
        # セッションが取得できることを確認
        session = Base.session()
        assert session is not None

        # データ操作
        test_record = Test1(unique_id="test_context")
        session.add(test_record)
        await session.commit()

        # select メソッドのテスト
        query = Test1.select().where(Test1.unique_id == "test_context")
        result = (await session.execute(query)).scalar_one()
        assert result.unique_id == "test_context"

    finally:
        await Base.close_session(token)


@pytest.mark.asyncio
async def test_async_mixin_to_dict() -> None:
    """to_dictメソッドのテスト。"""
    test_record = Test1(id=1, unique_id="test_dict")
    result = test_record.to_dict()

    assert result == {"id": 1, "unique_id": "test_dict"}

    # includes テスト
    result_includes = test_record.to_dict(includes=["unique_id"])
    assert result_includes == {"unique_id": "test_dict"}

    # excludes テスト
    result_excludes = test_record.to_dict(excludes=["id"])
    assert result_excludes == {"unique_id": "test_dict"}


@pytest.mark.asyncio
async def test_get_by_id(session: sqlalchemy.ext.asyncio.AsyncSession) -> None:
    """get_by_idのテスト。"""
    async with Base.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session.add(Test1(unique_id="test_get_by_id"))
    await session.commit()

    # 作成されたレコードのIDを取得
    created_record = (await session.execute(Test1.select().where(Test1.unique_id == "test_get_by_id"))).scalar_one()
    test_id = created_record.id

    assert (await Test1.get_by_id(test_id)).id == test_id  # type: ignore
    assert (await Test1.get_by_id(test_id + 1000)) is None
    assert (await Test1.get_by_id(test_id, for_update=True)).id == test_id  # type: ignore


@pytest.mark.asyncio
async def test_get_by_unique_id(session: sqlalchemy.ext.asyncio.AsyncSession) -> None:
    """get_by_unique_idのテスト。"""
    async with Base.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)
    test1 = Test1(unique_id=Test1.generate_unique_id())
    assert test1.unique_id is not None and len(test1.unique_id) == 43
    unique_id = test1.unique_id
    session.add(test1)
    await session.commit()

    # 作成されたレコードのIDを取得
    test_id = test1.id

    assert (await Test1.get_by_unique_id(unique_id)).id == test_id  # type: ignore
    assert (await Test1.get_by_unique_id(unique_id, allow_id=True)).id == test_id  # type: ignore
    assert (await Test1.get_by_unique_id(test_id)) is None
    assert (await Test1.get_by_unique_id(test_id, allow_id=True)).id == test_id  # type: ignore
    assert (await Test1.get_by_unique_id(str(test_id), allow_id=True)) is None


@pytest.mark.asyncio
async def test_await_for_connection() -> None:
    """await_for_connectionのテスト。"""
    # 正常系
    await pytilpack.sqlalchemy.await_for_connection("sqlite+aiosqlite:///:memory:", timeout=1.0)

    # 異常系: タイムアウト
    with pytest.raises(sqlalchemy.exc.OperationalError):
        await pytilpack.sqlalchemy.await_for_connection("sqlite+aiosqlite:////nonexistent/path/db.sqlite3", timeout=1.0)


@pytest.mark.asyncio
async def test_paginate() -> None:
    """paginateのテスト。"""
    # テスト専用のセッションを作成
    async with Base.session_scope() as session:
        async with Base.connect() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # テストデータを準備（10件）
        test_items = [Test1(unique_id=f"paginate_test_{i}") for i in range(1, 11)]
        for item in test_items:
            session.add(item)
        await session.commit()

        # 1ページあたり3件、1ページ目をテスト
        query = Test1.select().where(Test1.unique_id.like("paginate_test_%")).order_by(Test1.id)
        paginator = await Test1.paginate(query, page=1, per_page=3)

        assert paginator.page == 1
        assert paginator.per_page == 3
        assert paginator.total_items == 10
        assert len(paginator.items) == 3
        assert paginator.pages == 4
        assert paginator.has_next is True
        assert paginator.has_prev is False

        # 2ページ目をテスト
        paginator = await Test1.paginate(query, page=2, per_page=3)
        assert paginator.page == 2
        assert len(paginator.items) == 3
        assert paginator.has_next is True
        assert paginator.has_prev is True

        # 最終ページ（4ページ目）をテスト
        paginator = await Test1.paginate(query, page=4, per_page=3)
        assert paginator.page == 4
        assert len(paginator.items) == 1  # 最後は1件のみ
        assert paginator.has_next is False
        assert paginator.has_prev is True

        # 境界値テスト：無効なページ番号
        with pytest.raises(AssertionError):
            await Test1.paginate(query, page=0, per_page=3)

        with pytest.raises(AssertionError):
            await Test1.paginate(query, page=1, per_page=0)

        # 空のクエリの場合
        empty_query = Test1.select().where(Test1.id > 100000)
        paginator = await Test1.paginate(empty_query, page=1, per_page=3)
        assert paginator.total_items == 0
        assert len(paginator.items) == 0
        assert paginator.pages == 1


@pytest.mark.asyncio
async def test_asafe_close() -> None:
    """asafe_closeのテスト。"""
    engine = sqlalchemy.ext.asyncio.create_async_engine("sqlite+aiosqlite:///:memory:")
    session = sqlalchemy.ext.asyncio.AsyncSession(engine)
    await pytilpack.sqlalchemy.asafe_close(session)  # 正常ケース

    # エラーケース（既にクローズ済み）
    await session.close()
    await pytilpack.sqlalchemy.asafe_close(session)
    await pytilpack.sqlalchemy.asafe_close(session, log_level=None)


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
        "value4": "2021-01-01T00:00:00",
        "value5": None,
    }
    assert test2.to_dict(includes=["name", "value3"], exclude_none=True) == {"name": "test2"}


def test_describe() -> None:
    """describe()のテスト。"""
    desc = pytilpack.sqlalchemy.describe(Base)
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
| value0    | FLOAT        | NO     |       | 1.0        |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| value4    | DATETIME     | NO     |       | NULL       |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
| value5    | TEXT         | NO     |       | (function) |                |              |
+-----------+--------------+--------+-------+------------+----------------+--------------+
"""
    )
