import datetime as dt
import typing

import pytest
import sqlalchemy
import sqlalchemy.engine
import sqlalchemy.exc
import sqlalchemy.orm

import pytilpack.sqlalchemy


class Base(sqlalchemy.orm.DeclarativeBase):  # type: ignore[name-defined]
    __test__ = False


class Test1(Base, pytilpack.sqlalchemy.Mixin, pytilpack.sqlalchemy.UniqueIDMixin):  # pylint: disable=too-many-ancestors
    __test__ = False
    __tablename__ = "test"

    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(primary_key=True)
    unique_id: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(
        sqlalchemy.String(43), unique=True, nullable=True, doc="ユニークID"
    )


class Test2(Base, pytilpack.sqlalchemy.Mixin):  # pylint: disable=too-many-ancestors
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


@pytest.fixture(name="engine", scope="session", autouse=True)
def _engine() -> typing.Generator[sqlalchemy.engine.Engine, None, None]:
    engine = sqlalchemy.create_engine("sqlite:///:memory:")
    pytilpack.sqlalchemy.register_ping()
    Base.metadata.create_all(engine)
    yield engine


@pytest.fixture(name="session", scope="function")
def _session(engine: sqlalchemy.engine.Engine) -> typing.Generator[sqlalchemy.orm.Session, None, None]:
    with sqlalchemy.orm.Session(engine) as session:
        Test1.query = session.query(Test1)
        try:
            yield session
        finally:
            Test1.query = None


@pytest.fixture(autouse=True)
def _clean_tables(engine: sqlalchemy.engine.Engine) -> typing.Generator[None, None, None]:
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
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


def test_get_by_id(session: sqlalchemy.orm.Session) -> None:
    session.add(Test1(id=1))
    session.commit()

    assert Test1.get_by_id(1).id == 1  # type: ignore
    assert Test1.get_by_id(2) is None
    assert Test1.get_by_id(1, for_update=True).id == 1  # type: ignore


def test_get_by_id_not_null(session: sqlalchemy.orm.Session) -> None:
    session.add(Test1(id=10))
    session.commit()

    result = Test1.get_by_id_not_null(10)
    assert result.id == 10

    with pytest.raises(ValueError):
        Test1.get_by_id_not_null(9999)


def test_get_by_unique_id(session: sqlalchemy.orm.Session) -> None:
    test1 = Test1(id=2, unique_id=Test1.generate_unique_id())
    assert test1.unique_id is not None and len(test1.unique_id) == 43
    unique_id = test1.unique_id
    session.add(test1)
    session.commit()

    assert Test1.get_by_unique_id(unique_id).id == 2  # type: ignore
    assert Test1.get_by_unique_id(unique_id, allow_id=True).id == 2  # type: ignore
    assert Test1.get_by_unique_id(2) is None
    assert Test1.get_by_unique_id(2, allow_id=True).id == 2  # type: ignore
    assert Test1.get_by_unique_id("2", allow_id=True) is None


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
