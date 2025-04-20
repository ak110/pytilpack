"""SQLAlchemy用のユーティリティ集。(async版)"""

import asyncio
import contextlib
import contextvars
import logging
import secrets
import time
import typing

import sqlalchemy
import sqlalchemy.ext.asyncio

logger = logging.getLogger(__name__)


class AsyncMixin(sqlalchemy.ext.asyncio.AsyncAttrs):
    """モデルのベースクラス。SQLAlchemy 2.0スタイル・async前提。

    使用例::
        class Base(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy_.AsyncMixin):
            pass

        class User(Base):
            __tablename__ = "users"
            ...

    """

    engine: sqlalchemy.ext.asyncio.AsyncEngine | None = None
    """DB接続。"""

    sessionmaker: (
        sqlalchemy.ext.asyncio.async_sessionmaker[sqlalchemy.ext.asyncio.AsyncSession]
        | None
    ) = None
    """セッションファクトリ。"""

    session_var: contextvars.ContextVar[sqlalchemy.ext.asyncio.AsyncSession] = (
        contextvars.ContextVar("session_var")
    )
    """セッション。"""

    @classmethod
    def init(
        cls,
        url: str | sqlalchemy.engine.URL,
        autoflush: bool = True,
        expire_on_commit: bool = False,
        **kwargs,
    ):
        cls.engine = sqlalchemy.ext.asyncio.create_async_engine(url, **kwargs)
        cls.sessionmaker = sqlalchemy.ext.asyncio.async_sessionmaker(
            cls.engine, autoflush=autoflush, expire_on_commit=expire_on_commit
        )

    @classmethod
    def connect(cls) -> sqlalchemy.ext.asyncio.AsyncConnection:
        """DBに接続する。

        使用例::
            async with Base.connect() as conn:
                await conn.run_sync(Base.metadata.create_all)

        """
        assert cls.engine is not None
        return cls.engine.connect()

    @classmethod
    @contextlib.asynccontextmanager
    async def session_scope(cls):
        """セッションを開始するコンテキストマネージャ。

        使用例::
            async with Base.session_scope() as session:
                ...

        """
        assert cls.sessionmaker is not None
        token = await cls.start_session()
        try:
            yield cls.session()
        finally:
            await cls.close_session(token)

    @classmethod
    async def start_session(
        cls,
    ) -> contextvars.Token[sqlalchemy.ext.asyncio.AsyncSession]:
        """セッションを開始する。"""
        assert cls.sessionmaker is not None
        return cls.session_var.set(cls.sessionmaker())  # pylint: disable=not-callable

    @classmethod
    async def close_session(
        cls, token: contextvars.Token[sqlalchemy.ext.asyncio.AsyncSession]
    ) -> None:
        """セッションを終了する。"""
        await asafe_close(cls.session())
        cls.session_var.reset(token)

    @classmethod
    def session(cls) -> sqlalchemy.ext.asyncio.AsyncSession:
        """セッションを取得する。"""
        try:
            return cls.session_var.get()
        except LookupError as e:
            raise RuntimeError(
                "セッションが開始されていません。"
                f"{cls.__class__.__qualname__}.start_session()を呼び出してください。"
            ) from e

    @classmethod
    def select(cls) -> sqlalchemy.Select:
        """sqlalchemy.Selectを返す。"""
        return sqlalchemy.select(cls)

    @classmethod
    def insert(cls) -> sqlalchemy.Insert:
        """sqlalchemy.Insertを返す。"""
        return sqlalchemy.insert(cls)

    @classmethod
    def update(cls) -> sqlalchemy.Update:
        """sqlalchemy.Updateを返す。"""
        return sqlalchemy.update(cls)

    @classmethod
    def delete(cls) -> sqlalchemy.Delete:
        """sqlalchemy.Deleteを返す。"""
        return sqlalchemy.delete(cls)

    @classmethod
    async def get_by_id(cls, id_: int, for_update: bool = False) -> typing.Self | None:
        """IDを元にインスタンスを取得。

        Args:
            id_: ID。
            for_update: 更新ロックを取得するか否か。

        Returns:
            インスタンス。

        """
        async with cls.session() as session:
            q = cls.select().where(cls.id == id_)  # type: ignore  # pylint: disable=no-member
            if for_update:
                q = q.with_for_update()
            result = await session.execute(q)
            return result.scalar_one_or_none()

    def to_dict(
        self,
        includes: list[str] | None = None,
        excludes: list[str] | None = None,
        exclude_none: bool = False,
    ) -> dict[str, typing.Any]:
        """インスタンスを辞書化する。

        Args:
            includes: 辞書化するフィールド名のリスト。excludesと同時指定不可。
            excludes: 辞書化しないフィールド名のリスト。includesと同時指定不可。
            exclude_none: Noneのフィールドを除外するかどうか。

        Returns:
            辞書。

        """
        assert (includes is None) or (excludes is None)
        all_columns = [column.name for column in self.__table__.columns]  # type: ignore[attr-defined]
        if includes is None:
            includes = all_columns
            if excludes is None:
                pass
            else:
                assert (set(all_columns) & set(excludes)) == set(excludes)
                includes = list(filter(lambda x: x not in excludes, includes))
        else:
            assert excludes is None
            assert (set(all_columns) & set(includes)) == set(includes)
        return {
            column_name: getattr(self, column_name)
            for column_name in includes
            if not exclude_none or getattr(self, column_name) is not None
        }


class AsyncUniqueIDMixin:
    """self.unique_idを持つテーブルクラスに便利メソッドを生やすmixin。"""

    @classmethod
    def generate_unique_id(cls) -> str:
        """ユニークIDを生成する。"""
        return secrets.token_urlsafe(32)

    @classmethod
    async def get_by_unique_id(
        cls: type[typing.Self],
        unique_id: str | int,
        allow_id: bool = False,
        for_update: bool = False,
    ) -> typing.Self | None:
        """ユニークIDを元にインスタンスを取得。

        Args:
            unique_id: ユニークID。
            allow_id: ユニークIDだけでなくID(int)も許可するかどうか。
            for_update: 更新ロックを取得するか否か。

        Returns:
            インスタンス。

        """
        assert issubclass(cls, AsyncMixin)
        async with cls.session() as session:
            if allow_id and isinstance(unique_id, int):
                q = cls.select().where(cls.id == unique_id)  # type: ignore
            else:
                q = cls.select().where(cls.unique_id == unique_id)  # type: ignore
            if for_update:
                q = q.with_for_update()
            result = await session.execute(q)
            return result.scalar_one_or_none()


async def await_for_connection(url: str, timeout: float = 60.0) -> None:
    """DBに接続可能になるまで待機する。"""
    failed = False
    start_time = time.time()
    while True:
        try:
            engine = sqlalchemy.ext.asyncio.create_async_engine(url)
            try:
                async with engine.connect() as connection:
                    await connection.execute(sqlalchemy.text("SELECT 1"))
            finally:
                await engine.dispose()
            # 接続成功
            if failed:  # 過去に接続失敗していた場合だけログを出す
                logger.info("DB接続成功")
            break
        except Exception:
            # 接続失敗
            if not failed:
                failed = True
                logger.info(f"DB接続待機中 . . . (URL: {url})")
            if time.time() - start_time >= timeout:
                raise
            await asyncio.sleep(1)


async def asafe_close(
    session: sqlalchemy.ext.asyncio.AsyncSession, log_level: int | None = logging.DEBUG
):
    """例外を出さずにセッションをクローズ。"""
    try:
        await session.close()
    except Exception:
        if log_level is not None:
            logger.log(log_level, "セッションクローズ失敗", exc_info=True)
