import datetime as dt
import logging
import pathlib
import typing
import unittest.mock

import pytest
import sqlalchemy
import sqlalchemy.engine
import sqlalchemy.exc
import sqlalchemy.orm

import pytilpack.sqlalchemy


class Base(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy.SyncMixin):  # pylint: disable=too-many-ancestors
    pass


class Test1(Base, pytilpack.sqlalchemy.SyncUniqueIDMixin):  # pylint: disable=too-many-ancestors
    __test__ = False
    __tablename__ = "test1"

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


class Test3(Base, pytilpack.sqlalchemy.SyncUniqueIDMixin):  # pylint: disable=too-many-ancestors
    __test__ = False
    __tablename__ = "test3"

    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(primary_key=True)
    unique_id: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(
        sqlalchemy.String(43), unique=True, nullable=True, doc="ユニークID"
    )


@pytest.fixture(name="engine", scope="session", autouse=True)
def _engine() -> typing.Generator[sqlalchemy.engine.Engine, None, None]:
    # https://stackoverflow.com/questions/61678766/sqlalchemy-exc-operationalerror-sqlite3-operationalerror-no-such-table-items/61694048
    Base.init("sqlite:///:memory:?check_same_thread=false", poolclass=sqlalchemy.pool.StaticPool)
    assert Base.engine is not None
    Base.metadata.create_all(Base.engine)
    yield Base.engine


@pytest.fixture(name="session", scope="function")
def _session() -> typing.Generator[sqlalchemy.orm.Session, None, None]:
    with Base.session_scope() as session:
        yield session


@pytest.fixture(autouse=True)
def _clean_tables() -> typing.Generator[None, None, None]:
    with Base.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()
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


def test_mixin_basic_functionality() -> None:
    with Base.session_scope():
        assert Base.count(Test1.select()) == 0

        test_record = Test1(unique_id="test_name")
        Base.session().add(test_record)
        Base.session().commit()

        result = Test1.get_by_id(test_record.id)
        assert result is not None
        assert result.unique_id == "test_name"

        assert Base.count(Test1.select()) == 1

        Base.session().execute(Test1.delete())
        Base.session().commit()

        assert Base.count(Test1.select()) == 0


def test_sync_mixin_context_vars() -> None:
    with Base.session_scope() as outer:
        assert Base.session() is outer
        with Base.session_scope() as inner:
            assert inner is not outer
            assert Base.session() is inner
        assert Base.session() is outer
    with pytest.raises(RuntimeError):
        Base.session()


def test_sync_mixin_to_dict() -> None:
    test_record = Test1(id=1, unique_id="test_dict")
    result = test_record.to_dict()

    assert result == {"id": 1, "unique_id": "test_dict"}

    result_includes = test_record.to_dict(includes=["unique_id"])
    assert result_includes == {"unique_id": "test_dict"}

    result_excludes = test_record.to_dict(excludes=["id"])
    assert result_excludes == {"unique_id": "test_dict"}


def test_get_by_id(session: sqlalchemy.orm.Session) -> None:
    session.add(Test1(unique_id="test_get_by_id"))
    session.commit()

    created_record = session.execute(Test1.select().where(Test1.unique_id == "test_get_by_id")).scalar_one()
    test_id = created_record.id

    assert Test1.get_by_id(test_id).id == test_id  # type: ignore
    assert Test1.get_by_id(test_id + 1000) is None
    assert Test1.get_by_id(test_id, for_update=True).id == test_id  # type: ignore


def test_get_by_id_not_null(session: sqlalchemy.orm.Session) -> None:
    session.add(Test1(unique_id="test_get_by_id_not_null"))
    session.commit()

    created_record = session.execute(Test1.select().where(Test1.unique_id == "test_get_by_id_not_null")).scalar_one()
    test_id = created_record.id

    result = Test1.get_by_id_not_null(test_id)
    assert result.id == test_id

    with pytest.raises(ValueError):
        Test1.get_by_id_not_null(test_id + 1000)


def test_get_by_unique_id(session: sqlalchemy.orm.Session) -> None:
    test1 = Test1(unique_id=Test1.generate_unique_id())
    assert test1.unique_id is not None and len(test1.unique_id) == 43
    unique_id = test1.unique_id
    session.add(test1)
    session.commit()

    test_id = test1.id

    assert Test1.get_by_unique_id(unique_id).id == test_id  # type: ignore
    assert Test1.get_by_unique_id(unique_id, allow_id=True).id == test_id  # type: ignore
    assert Test1.get_by_unique_id(test_id) is None
    assert Test1.get_by_unique_id(test_id, allow_id=True).id == test_id  # type: ignore
    assert Test1.get_by_unique_id(str(test_id), allow_id=True) is None


def test_to_dict_invalid_args() -> None:
    test_record = Test1(id=1, unique_id="test_dict")

    with pytest.raises(ValueError):
        test_record.to_dict(includes=["id"], excludes=["unique_id"])

    with pytest.raises(ValueError):
        test_record.to_dict(includes=["nonexistent"])

    with pytest.raises(ValueError):
        test_record.to_dict(excludes=["nonexistent"])


def test_init_already_called() -> None:

    class TempBase(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy.SyncMixin):  # pylint: disable=too-many-ancestors
        pass

    TempBase.init("sqlite:///:memory:?check_same_thread=false", poolclass=sqlalchemy.pool.StaticPool)
    try:
        with pytest.raises(RuntimeError, match="すでに初期化"):
            TempBase.init("sqlite:///:memory:?check_same_thread=false", poolclass=sqlalchemy.pool.StaticPool)
    finally:
        if TempBase.engine is not None:
            TempBase.engine.dispose()


def test_wait_for_connection(tmp_path: pathlib.Path) -> None:
    pytilpack.sqlalchemy.wait_for_connection("sqlite:///:memory:", timeout=0.1)

    db = tmp_path / "missing" / "db.sqlite3"
    with pytest.raises(RuntimeError) as error:
        pytilpack.sqlalchemy.wait_for_connection(f"sqlite:///{db}", timeout=0.1)
    assert isinstance(error.value.__cause__, sqlalchemy.exc.OperationalError)


def test_paginate() -> None:
    with Base.session_scope() as session:
        test_items = [Test1(unique_id=f"paginate_test_{i}") for i in range(1, 11)]
        for item in test_items:
            session.add(item)
        session.commit()

        query = Test1.select().where(Test1.unique_id.like("paginate_test_%")).order_by(Test1.id)
        paginator = Test1.paginate(query, page=1, per_page=3)

        assert paginator.page == 1
        assert paginator.per_page == 3
        assert paginator.total_items == 10
        assert [item.unique_id for item in paginator.items] == [f"paginate_test_{i}" for i in range(1, 4)]
        assert paginator.pages == 4
        assert paginator.has_next is True
        assert paginator.has_prev is False

        paginator = Test1.paginate(query, page=2, per_page=3)
        assert paginator.page == 2
        assert [item.unique_id for item in paginator.items] == [f"paginate_test_{i}" for i in range(4, 7)]
        assert paginator.has_next is True
        assert paginator.has_prev is True

        paginator = Test1.paginate(query, page=4, per_page=3)
        assert paginator.page == 4
        assert [item.unique_id for item in paginator.items] == ["paginate_test_10"]
        assert paginator.has_next is False
        assert paginator.has_prev is True

        with pytest.raises(ValueError):
            Test1.paginate(query, page=0, per_page=3)

        with pytest.raises(ValueError):
            Test1.paginate(query, page=1, per_page=0)

        empty_query = Test1.select().where(Test1.id > 100000)
        paginator = Test1.paginate(empty_query, page=1, per_page=3)
        assert paginator.total_items == 0
        assert len(paginator.items) == 0
        assert paginator.pages == 1


def test_safe_close() -> None:
    assert Base.engine is not None
    with sqlalchemy.orm.Session(Base.engine) as session:
        session.add(Test1(unique_id="uncommitted"))
        session.flush()
        pytilpack.sqlalchemy.safe_close(session)
        assert not session.in_transaction()
        pytilpack.sqlalchemy.safe_close(session)

    with Base.session_scope() as observer:
        assert observer.scalar(sqlalchemy.select(Test1).where(Test1.unique_id == "uncommitted")) is None


@pytest.mark.parametrize("log_level", [logging.ERROR, None])
def test_safe_close_suppresses_close_error(caplog: pytest.LogCaptureFixture, log_level: int | None) -> None:
    session = sqlalchemy.orm.Session()
    close = unittest.mock.Mock(side_effect=RuntimeError("close failed"))
    with unittest.mock.patch.object(session, "close", close):
        pytilpack.sqlalchemy.safe_close(session, log_level=log_level)
    close.assert_called_once_with()
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

    # arid: enable


@pytest.mark.asyncio
async def test_async_methods() -> None:

    with Base.session_scope():
        test_records = [Test3(unique_id=f"async_test_{i}") for i in range(1, 6)]
        for record in test_records:
            Base.session().add(record)
        Base.commit()

        count = Test3.count(Test3.select().where(Test3.unique_id.like("async_test_%")))
        assert count == 5

        count = await Test3.acount(Test3.select().where(Test3.unique_id.like("async_test_%")))
        assert count == 5

        result = await Test3.ascalar_one_or_none(Test3.select().where(Test3.unique_id == "async_test_1"))
        assert result is not None
        assert result.unique_id == "async_test_1"

        names = [f"async_test_{i}" for i in range(1, 6)]
        results = await Test3.ascalars(sqlalchemy.select(Test3.unique_id).order_by(Test3.id))
        assert list(results) == names

        columns = sqlalchemy.select(Test3.id, Test3.unique_id)
        test_id = test_records[0].id
        row = await Test3.aone_or_none(columns.where(Test3.id == test_id))
        assert isinstance(row, sqlalchemy.Row)
        assert tuple(row) == (test_id, names[0])

        rows = await Test3.aall(columns.order_by(Test3.id))
        assert all(isinstance(row, sqlalchemy.Row) for row in rows)
        assert [tuple(row) for row in rows] == list(zip([record.id for record in test_records], names, strict=True))

        result_by_id = await Test3.aget_by_id(test_id)
        assert result_by_id is not None
        assert result_by_id.id == test_id

        query = Test3.select().where(Test3.unique_id.like("async_test_%")).order_by(Test3.id)
        paginator = await Test3.apaginate(query, page=1, per_page=3)
        assert paginator.page == 1
        assert paginator.per_page == 3
        assert paginator.total_items == 5
        assert [item.unique_id for item in paginator.items] == names[:3]
        assert paginator.pages == 2
