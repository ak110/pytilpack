"""テストコード。"""

import asyncio
import threading
import typing

import pytest
import sqlalchemy
import sqlalchemy.orm

import pytilpack.sqlalchemy.async_


def _make_base() -> tuple[typing.Any, typing.Any]:
    """テスト用のBaseクラスとItemクラスを生成する。テストごとに独立したクラスが必要。"""

    class Base(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy.async_.AsyncMixin):
        """テスト用ベースクラス。"""

    class Item(Base):
        """テスト用アイテムクラス。"""

        __tablename__ = "items"
        id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(primary_key=True, autoincrement=True)
        name: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column()

    return Base, Item


@pytest.mark.asyncio
async def test_basic(tmp_path):
    """基本的な動作テスト: init/session_scope/term。"""
    Base, Item = _make_base()
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    Base.init(url)
    try:
        async with Base.connect() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with Base.session_scope() as session:
            session.add(Item(name="hello"))
            await session.commit()

        async with Base.session_scope() as session:
            items = await Item.scalars(Item.select())
            assert len(items) == 1
            assert items[0].name == "hello"
    finally:
        await Base.term()


@pytest.mark.asyncio
async def test_thread_local_isolation(tmp_path):
    """異なるスレッドでは別々のengineが生成されることを確認する。"""
    Base, _ = _make_base()
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    Base.init(url)

    engines: list[int] = []
    errors: list[Exception] = []

    def run_in_thread() -> None:
        async def inner() -> None:
            engine = Base.engine()
            assert engine is not None
            engines.append(id(engine))
            await Base.term()

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
async def test_term_resets_thread_local(tmp_path):
    """term()後に再度アクセスすると新しいengineが生成されることを確認する。"""
    Base, _ = _make_base()
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    Base.init(url)

    engine1 = Base.engine()
    await Base.term()
    engine2 = Base.engine()
    await Base.term()

    assert id(engine1) != id(engine2), "term()後も同じengineインスタンスが返された"


@pytest.mark.asyncio
async def test_init_args_stored_globally(tmp_path):
    """_init_argsがクラス変数として保持されていることを確認する。"""
    Base, _ = _make_base()
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    Base.init(url)
    try:
        assert Base._init_args is not None  # pylint: disable=protected-access
        assert str(Base._init_args.url) == url  # pylint: disable=protected-access
    finally:
        await Base.term()


@pytest.mark.asyncio
async def test_same_thread_reuses_engine(tmp_path):
    """同じスレッド内では同じengineが再利用されることを確認する。"""
    Base, _ = _make_base()
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    Base.init(url)
    try:
        engine1 = Base.engine()
        engine2 = Base.engine()
        assert id(engine1) == id(engine2), "同じスレッド内で異なるengineが返された"
    finally:
        await Base.term()
