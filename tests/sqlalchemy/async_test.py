"""async版のテストコード。"""

import asyncio
import datetime
import threading
import typing

import pytest
import pytest_asyncio
import sqlalchemy
import sqlalchemy.ext.asyncio
import sqlalchemy.orm

import pytilpack.sqlalchemy


class Base(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy.AsyncMixin):
    """ベースクラス。"""


class Test1(Base, pytilpack.sqlalchemy.AsyncUniqueIDMixin):  # pylint: disable=too-many-ancestors
    """テストクラス。"""

    __test__ = False
    __tablename__ = "test"

    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(primary_key=True)
    unique_id: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(
        sqlalchemy.String(43), unique=True, nullable=True, doc="ユニークID"
    )


class Test2(Base):  # pylint: disable=too-many-ancestors
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
    try:
        yield Base.engine()
    finally:
        await Base.term()


@pytest_asyncio.fixture(name="session", scope="module")
async def _session() -> typing.AsyncGenerator[sqlalchemy.ext.asyncio.AsyncSession, None]:
    """セッション。"""
    async with Base.session_scope() as session:
        yield session


def test_repr() -> None:
    """__repr__のテスト。"""
    # デフォルト: idを表示
    test1 = Test1(id=1)
    r = repr(test1)
    assert r == f"<{Test1.__module__}.{Test1.__qualname__}(id=1)>"
    assert str(test1) == r

    # idがNoneの場合
    test1_no_id = Test1()
    assert repr(test1_no_id) == f"<{Test1.__module__}.{Test1.__qualname__}(id=None)>"

    # _repr_attrsをオーバーライドしたケース
    class CustomRepr(Test1):  # pylint: disable=too-many-ancestors
        """カスタムreprのテスト用クラス。"""

        __test__ = False

        @typing.override
        def _repr_attrs(self):
            return {"id": self.id, "unique_id": self.unique_id}

    custom = CustomRepr(id=42, unique_id="abc")
    assert "id=42" in repr(custom)
    assert "unique_id='abc'" in repr(custom)


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

    async with Base.session_scope():
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
    await pytilpack.sqlalchemy.await_for_connection("sqlite+aiosqlite:///:memory:", timeout=0.1)

    # 異常系: タイムアウト
    with pytest.raises(RuntimeError):
        await pytilpack.sqlalchemy.await_for_connection("sqlite+aiosqlite:////nonexistent/path/db.sqlite3", timeout=0.1)


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

        # 境界値テスト：無効なページ番号（ValueErrorに変更）
        with pytest.raises(ValueError):
            await Test1.paginate(query, page=0, per_page=3)

        with pytest.raises(ValueError):
            await Test1.paginate(query, page=1, per_page=0)

        # 空のクエリの場合
        empty_query = Test1.select().where(Test1.id > 100000)
        paginator = await Test1.paginate(empty_query, page=1, per_page=3)
        assert paginator.total_items == 0
        assert len(paginator.items) == 0
        assert paginator.pages == 1


@pytest.mark.asyncio
async def test_async_init_already_called() -> None:
    """AsyncMixin.init()二重呼び出し時にRuntimeErrorが送出されることを確認。

    assert文からRuntimeErrorに変更したため、`-O`実行時も検証が効く。
    """

    class TempBase(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy.AsyncMixin):
        """テスト専用Base。グローバル状態を汚染しないよう個別クラスで検証する。"""

    TempBase.init("sqlite+aiosqlite:///:memory:")
    try:
        with pytest.raises(RuntimeError, match="すでに初期化"):
            TempBase.init("sqlite+aiosqlite:///:memory:")
    finally:
        await TempBase.term()


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


def _make_isolated_base() -> tuple[typing.Any, typing.Any]:
    """テストごとに独立したBaseクラスとItemクラスを生成する。"""

    class IsolatedBase(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy.AsyncMixin):
        """テスト用ベースクラス。"""

    class Item(IsolatedBase):  # pylint: disable=too-many-ancestors
        """テスト用アイテムクラス。"""

        __tablename__ = "items"
        id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(primary_key=True, autoincrement=True)
        name: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column()

    return IsolatedBase, Item


@pytest.mark.asyncio
async def test_engine_init_and_scalars(tmp_path) -> None:
    """init/session_scope/term および scalars メソッドの基本テスト。"""
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
    """異なるスレッドでは別々のengineが生成されることを確認する。"""
    IsolatedBase, _ = _make_isolated_base()
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    IsolatedBase.init(url)

    engines: list[int] = []
    errors: list[Exception] = []

    def run_in_thread() -> None:
        async def inner() -> None:
            engine = IsolatedBase.engine()
            assert engine is not None
            engines.append(id(engine))
            await IsolatedBase.term()

        try:
            asyncio.run(inner())
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=run_in_thread) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"スレッド内でエラーが発生: {errors}"
    assert len(engines) == 2
    # 別々のスレッドからは別々のengineインスタンスが生成される
    assert engines[0] != engines[1], "異なるスレッドが同じengineを共有している"


@pytest.mark.asyncio
async def test_term_resets_engine(tmp_path) -> None:
    """term()後に再度アクセスすると新しいengineが生成されることを確認する。"""
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
    """_init_argsがクラス変数として保持されていることを確認する。"""
    IsolatedBase, _ = _make_isolated_base()
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    IsolatedBase.init(url)
    try:
        assert IsolatedBase._init_args is not None  # pylint: disable=protected-access
        assert str(IsolatedBase._init_args.url) == url  # pylint: disable=protected-access
    finally:
        await IsolatedBase.term()


@pytest.mark.asyncio
async def test_negative_pool_size_uses_null_pool(tmp_path) -> None:
    """pool_sizeが負数ならNullPoolで初期化されることを確認する。"""
    IsolatedBase, _ = _make_isolated_base()
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    IsolatedBase.init(url, pool_size=-1)
    try:
        engine = IsolatedBase.engine()
        assert isinstance(engine.sync_engine.pool, sqlalchemy.pool.NullPool)
    finally:
        await IsolatedBase.term()


@pytest.mark.asyncio
async def test_same_thread_reuses_engine(tmp_path) -> None:
    """同じスレッド内では同じengineが再利用されることを確認する。"""
    IsolatedBase, _ = _make_isolated_base()
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    IsolatedBase.init(url)
    try:
        engine1 = IsolatedBase.engine()
        engine2 = IsolatedBase.engine()
        assert id(engine1) == id(engine2), "同じスレッド内で異なるengineが返された"
    finally:
        await IsolatedBase.term()


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
