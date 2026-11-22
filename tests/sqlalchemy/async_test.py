import asyncio
import datetime as dt
import logging
import pathlib
import threading
import typing
import unittest.mock

import pytest
import pytest_asyncio
import sqlalchemy
import sqlalchemy.exc
import sqlalchemy.ext.asyncio
import sqlalchemy.orm

import pytilpack.sqlalchemy


class Base(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy.AsyncMixin):  # pylint: disable=too-many-ancestors
    pass


class Test1(Base, pytilpack.sqlalchemy.AsyncUniqueIDMixin):  # pylint: disable=too-many-ancestors
    __test__ = False
    __tablename__ = "test"

    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(primary_key=True)
    unique_id: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(
        sqlalchemy.String(43), unique=True, nullable=True, doc="ユニークID"
    )


class Test2(Base):  # pylint: disable=too-many-ancestors
    # arid: disable
    __test__ = False
    __tablename__ = "test2"
    __table_args__ = (sqlalchemy.UniqueConstraint("value1", "value2", name="uc1"),)

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String(250), nullable=False, unique=True, doc="名前")
    pass_hash = sqlalchemy.Column(sqlalchemy.String(100), default=None, comment="パスハッシュ")
    # 有効フラグ
    enabled = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=True)
    is_admin = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)
    value1 = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, default=0)
    value2 = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, default=512)
    value3 = sqlalchemy.Column("value0", sqlalchemy.Float, nullable=False, default=1.0)
    value4 = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
    value5 = sqlalchemy.Column(sqlalchemy.Text, nullable=False, default=lambda: "func")
    # arid: enable


@pytest_asyncio.fixture(name="engine", scope="session", autouse=True)
async def _engine() -> typing.AsyncGenerator[sqlalchemy.ext.asyncio.AsyncEngine, None]:
    Base.init("sqlite+aiosqlite:///:memory:")
    try:
        async with Base.engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield Base.engine()
    finally:
        await Base.term()


@pytest_asyncio.fixture(name="session", scope="function")
async def _session() -> typing.AsyncGenerator[sqlalchemy.ext.asyncio.AsyncSession, None]:
    async with Base.session_scope() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables() -> typing.AsyncGenerator[None, None]:
    async with Base.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
        await conn.commit()
    yield


def test_repr() -> None:
    # arid: disable
    test1 = Test1(id=1)
    r = repr(test1)
    assert r == f"<{Test1.__module__}.{Test1.__qualname__}(id=1)>"
    assert str(test1) == r

    test1_no_id = Test1()
    assert repr(test1_no_id) == f"<{Test1.__module__}.{Test1.__qualname__}(id=None)>"

    class CustomRepr(Test1):  # pylint: disable=too-many-ancestors
        __test__ = False

        @typing.override
        def _repr_attrs(self):
            return {"id": self.id, "unique_id": self.unique_id}

    custom = CustomRepr(id=42, unique_id="abc")
    assert "id=42" in repr(custom)
    assert "unique_id='abc'" in repr(custom)
    # arid: enable


@pytest.mark.asyncio
async def test_mixin_basic_functionality() -> None:
    async with Base.session_scope():
        assert await Base.count(Test1.select()) == 0

        test_record = Test1(unique_id="test_name")
        Base.session().add(test_record)
        await Base.session().commit()

        result = await Test1.get_by_id(test_record.id)
        assert result is not None
        assert result.unique_id == "test_name"

        assert await Base.count(Test1.select()) == 1

        await Base.session().execute(Test1.delete())
        await Base.session().commit()

        assert await Base.count(Test1.select()) == 0


@pytest.mark.asyncio
async def test_async_mixin_context_vars() -> None:
    async with Base.session_scope() as outer:
        assert Base.session() is outer
        async with Base.session_scope() as inner:
            assert inner is not outer
            assert Base.session() is inner
        assert Base.session() is outer
    with pytest.raises(RuntimeError):
        Base.session()


@pytest.mark.asyncio
async def test_async_mixin_to_dict() -> None:
    test_record = Test1(id=1, unique_id="test_dict")
    result = test_record.to_dict()

    assert result == {"id": 1, "unique_id": "test_dict"}

    result_includes = test_record.to_dict(includes=["unique_id"])
    assert result_includes == {"unique_id": "test_dict"}

    result_excludes = test_record.to_dict(excludes=["id"])
    assert result_excludes == {"unique_id": "test_dict"}


@pytest.mark.asyncio
async def test_get_by_id(session: sqlalchemy.ext.asyncio.AsyncSession) -> None:
    session.add(Test1(unique_id="test_get_by_id"))
    await session.commit()

    created_record = (await session.execute(Test1.select().where(Test1.unique_id == "test_get_by_id"))).scalar_one()
    test_id = created_record.id

    assert (await Test1.get_by_id(test_id)).id == test_id  # type: ignore
    assert (await Test1.get_by_id(test_id + 1000)) is None
    assert (await Test1.get_by_id(test_id, for_update=True)).id == test_id  # type: ignore


@pytest.mark.asyncio
async def test_get_by_unique_id(session: sqlalchemy.ext.asyncio.AsyncSession) -> None:
    test1 = Test1(unique_id=Test1.generate_unique_id())
    assert test1.unique_id is not None and len(test1.unique_id) == 43
    unique_id = test1.unique_id
    session.add(test1)
    await session.commit()

    test_id = test1.id

    assert (await Test1.get_by_unique_id(unique_id)).id == test_id  # type: ignore
    assert (await Test1.get_by_unique_id(unique_id, allow_id=True)).id == test_id  # type: ignore
    assert (await Test1.get_by_unique_id(test_id)) is None
    assert (await Test1.get_by_unique_id(test_id, allow_id=True)).id == test_id  # type: ignore
    assert (await Test1.get_by_unique_id(str(test_id), allow_id=True)) is None


@pytest.mark.asyncio
async def test_await_for_connection(tmp_path: pathlib.Path) -> None:
    await pytilpack.sqlalchemy.await_for_connection("sqlite+aiosqlite:///:memory:", timeout=0.1)

    db = tmp_path / "missing" / "db.sqlite3"
    with pytest.raises(RuntimeError) as error:
        await pytilpack.sqlalchemy.await_for_connection(f"sqlite+aiosqlite:///{db}", timeout=0.1)
    assert isinstance(error.value.__cause__, sqlalchemy.exc.OperationalError)


@pytest.mark.asyncio
async def test_paginate() -> None:
    async with Base.session_scope() as session:
        test_items = [Test1(unique_id=f"paginate_test_{i}") for i in range(1, 11)]
        for item in test_items:
            session.add(item)
        await session.commit()

        query = Test1.select().where(Test1.unique_id.like("paginate_test_%")).order_by(Test1.id)
        paginator = await Test1.paginate(query, page=1, per_page=3)

        assert paginator.page == 1
        assert paginator.per_page == 3
        assert paginator.total_items == 10
        assert [item.unique_id for item in paginator.items] == [f"paginate_test_{i}" for i in range(1, 4)]
        assert paginator.pages == 4
        assert paginator.has_next is True
        assert paginator.has_prev is False

        paginator = await Test1.paginate(query, page=2, per_page=3)
        assert paginator.page == 2
        assert [item.unique_id for item in paginator.items] == [f"paginate_test_{i}" for i in range(4, 7)]
        assert paginator.has_next is True
        assert paginator.has_prev is True

        paginator = await Test1.paginate(query, page=4, per_page=3)
        assert paginator.page == 4
        assert [item.unique_id for item in paginator.items] == ["paginate_test_10"]
        assert paginator.has_next is False
        assert paginator.has_prev is True

        with pytest.raises(ValueError):
            await Test1.paginate(query, page=0, per_page=3)

        with pytest.raises(ValueError):
            await Test1.paginate(query, page=1, per_page=0)

        empty_query = Test1.select().where(Test1.id > 100000)
        paginator = await Test1.paginate(empty_query, page=1, per_page=3)
        assert paginator.total_items == 0
        assert len(paginator.items) == 0
        assert paginator.pages == 1


@pytest.mark.asyncio
async def test_async_init_already_called() -> None:

    class TempBase(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy.AsyncMixin):  # pylint: disable=too-many-ancestors
        pass

    TempBase.init("sqlite+aiosqlite:///:memory:")
    try:
        with pytest.raises(RuntimeError, match="すでに初期化"):
            TempBase.init("sqlite+aiosqlite:///:memory:")
    finally:
        await TempBase.term()


@pytest.mark.asyncio
async def test_asafe_close() -> None:
    assert Base.engine() is not None
    async with sqlalchemy.ext.asyncio.AsyncSession(Base.engine()) as session:
        session.add(Test1(unique_id="uncommitted"))
        await session.flush()
        await pytilpack.sqlalchemy.asafe_close(session)
        assert not session.in_transaction()
        await pytilpack.sqlalchemy.asafe_close(session)

    async with Base.session_scope() as observer:
        assert await observer.scalar(sqlalchemy.select(Test1).where(Test1.unique_id == "uncommitted")) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("log_level", [logging.ERROR, None])
async def test_asafe_close_suppresses_close_error(caplog: pytest.LogCaptureFixture, log_level: int | None) -> None:
    session = sqlalchemy.ext.asyncio.AsyncSession()
    close = unittest.mock.AsyncMock(side_effect=RuntimeError("close failed"))
    with unittest.mock.patch.object(session, "close", close):
        await pytilpack.sqlalchemy.asafe_close(session, log_level=log_level)
    close.assert_awaited_once_with()
    assert [record.levelno for record in caplog.records if "close failed" in str(record.exc_info)] == (
        [] if log_level is None else [log_level]
    )


def test_to_dict() -> None:
    # arid: disable
    test2 = Test2(name="test2", enabled=True, value4=dt.datetime(2021, 1, 1))
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
    # arid: enable


def _make_isolated_base() -> tuple[typing.Any, typing.Any]:

    class IsolatedBase(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy.AsyncMixin):  # pylint: disable=too-many-ancestors
        pass

    class Item(IsolatedBase):  # pylint: disable=too-many-ancestors
        __tablename__ = "items"
        id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(primary_key=True, autoincrement=True)
        name: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column()

    return IsolatedBase, Item


@pytest.mark.asyncio
async def test_engine_init_and_scalars(tmp_path) -> None:
    IsolatedBase, Item = _make_isolated_base()
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    IsolatedBase.init(url)
    try:
        async with IsolatedBase.connect() as conn:
            await conn.run_sync(IsolatedBase.metadata.create_all)

        async with IsolatedBase.session_scope() as session:
            session.add(Item(name="hello"))
            await session.commit()

        async with IsolatedBase.session_scope():
            items = await Item.scalars(Item.select())
            assert len(items) == 1
            assert items[0].name == "hello"
    finally:
        await IsolatedBase.term()


@pytest.mark.asyncio
async def test_thread_local_engine_isolation(tmp_path) -> None:
    IsolatedBase, _ = _make_isolated_base()
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    IsolatedBase.init(url)

    engines: list = []
    errors: list[Exception] = []
    barrier = threading.Barrier(2, timeout=5)

    def run_in_thread() -> None:
        async def inner() -> None:
            engine = IsolatedBase.engine()
            assert engine is not None
            engines.append(engine)
            try:
                barrier.wait()
                assert len(engines) == 2
                assert engines[0] is not engines[1], "異なるスレッドが同じengineを共有している"
                barrier.wait()
            finally:
                await IsolatedBase.term()

        try:
            asyncio.run(inner())
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=run_in_thread) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
        assert not t.is_alive()

    assert not errors, f"スレッド内でエラーが発生: {errors}"
    assert len(engines) == 2
    assert engines[0] is not engines[1], "異なるスレッドが同じengineを共有している"


@pytest.mark.asyncio
async def test_term_resets_engine(tmp_path) -> None:
    IsolatedBase, _ = _make_isolated_base()
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    IsolatedBase.init(url)

    engine1 = IsolatedBase.engine()
    await IsolatedBase.term()
    engine2 = IsolatedBase.engine()
    await IsolatedBase.term()

    assert id(engine1) != id(engine2), "term()後も同じengineインスタンスが返された"


@pytest.mark.asyncio
async def test_init_args_stored_globally(tmp_path) -> None:
    IsolatedBase, _ = _make_isolated_base()
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    IsolatedBase.init(url)
    try:
        engine = IsolatedBase.engine()
        # 文字列表記はURLエンコードの有無（Windowsのパス区切りなど）で変わるため、解析後のURLで比べる
        assert engine.url == sqlalchemy.make_url(url)
    finally:
        await IsolatedBase.term()


@pytest.mark.asyncio
async def test_negative_pool_size_does_not_reuse_connection(tmp_path) -> None:
    IsolatedBase, _ = _make_isolated_base()
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    IsolatedBase.init(url, pool_size=-1)
    try:
        engine = IsolatedBase.engine()
        async with engine.begin() as conn:
            await conn.exec_driver_sql("CREATE TABLE persistent_value (value INTEGER)")
            await conn.exec_driver_sql("INSERT INTO persistent_value VALUES (42)")
            await conn.exec_driver_sql("CREATE TEMP TABLE connection_marker (value INTEGER)")
        async with engine.connect() as conn:
            assert (await conn.exec_driver_sql("SELECT value FROM persistent_value")).scalar_one() == 42
            assert (
                await conn.exec_driver_sql("SELECT name FROM sqlite_temp_master WHERE name = 'connection_marker'")
            ).scalar_one_or_none() is None
    finally:
        await IsolatedBase.term()


@pytest.mark.asyncio
async def test_same_thread_reuses_engine(tmp_path) -> None:
    IsolatedBase, _ = _make_isolated_base()
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    IsolatedBase.init(url)
    try:
        engine1 = IsolatedBase.engine()
        engine2 = IsolatedBase.engine()
        assert id(engine1) == id(engine2), "同じスレッド内で異なるengineが返された"
    finally:
        await IsolatedBase.term()

    # arid: enable
