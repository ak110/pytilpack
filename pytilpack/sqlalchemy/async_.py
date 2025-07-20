"""SQLAlchemy用のユーティリティ集（async版）。"""

import asyncio
import contextlib
import contextvars
import datetime
import logging
import secrets
import time
import typing

import sqlalchemy
import sqlalchemy.ext.asyncio

import pytilpack._paginator

logger = logging.getLogger(__name__)

T = typing.TypeVar("T")
TT = typing.TypeVar("TT", bound=tuple)


class AsyncMixin(sqlalchemy.ext.asyncio.AsyncAttrs):
    """モデルのベースクラス。SQLAlchemy 2.0スタイル・async前提。

    Examples:
        モデル定義例::

            class Base(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy_.AsyncMixin):
                pass

            class User(Base):
                __tablename__ = "users"
                ...

        Quart例::

            @app.before_request
            async def _before_request() -> None:
                quart.g.db_session_token = await models.Base.start_session()

            @app.teardown_request
            async def _teardown_request(_: BaseException | None) -> None:
                if hasattr(quart.g, "db_session_token"):
                    await models.Base.close_session(quart.g.db_session_token)
                    del quart.g.db_session_token

    """

    engine: sqlalchemy.ext.asyncio.AsyncEngine | None = None
    """DB接続。"""

    sessionmaker: sqlalchemy.ext.asyncio.async_sessionmaker[sqlalchemy.ext.asyncio.AsyncSession] | None = None
    """セッションファクトリ。"""

    session_var: contextvars.ContextVar[sqlalchemy.ext.asyncio.AsyncSession] = contextvars.ContextVar("session_var")
    """セッション。"""

    @classmethod
    def init(
        cls,
        url: str | sqlalchemy.engine.URL,
        pool_size: int | None = None,
        max_overflow: int | None = None,
        pool_recycle: int | None = 280,
        pool_pre_ping: bool = True,
        autoflush: bool = True,
        expire_on_commit: bool = False,
        **kwargs,
    ):
        """DB接続を初期化する。(デフォルトである程度おすすめの設定をしちゃう。)

        Args:
            url: DB接続URL。
            pool_size: コネクションプールのサイズ。スレッド数に応じて調整要。
            max_overflow: コネクションプールの最大オーバーフロー数。Noneの場合はデフォルト値を使用。
            pool_recycle: コネクションプールのリサイクル時間。Noneの場合はデフォルト値を使用。
            pool_pre_ping: コネクションプールのプレピン。Noneの場合はデフォルト値を使用。
            autoflush: セッションのautoflushフラグ。デフォルトはTrue。
            expire_on_commit: セッションのexpire_on_commitフラグ。デフォルトはFalse。

        """
        assert cls.engine is None, "DB接続はすでに初期化されています。"

        if pool_size is not None and max_overflow is None:
            max_overflow = pool_size * 1  # デフォルトで倍まで許可
        kwargs = kwargs.copy()
        if pool_size is not None:
            kwargs["pool_size"] = pool_size
        if max_overflow is not None:
            kwargs["max_overflow"] = max_overflow
        if pool_recycle is not None:
            kwargs["pool_recycle"] = pool_recycle
        if pool_pre_ping is not None:
            kwargs["pool_pre_ping"] = pool_pre_ping

        cls.engine = sqlalchemy.ext.asyncio.create_async_engine(url, **kwargs)
        # atexit.register(cls.engine.dispose)

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
    async def close_session(cls, token: contextvars.Token[sqlalchemy.ext.asyncio.AsyncSession]) -> None:
        """セッションを終了する。"""
        await asafe_close(cls.session())
        cls.session_var.reset(token)

    @classmethod
    def session(cls) -> sqlalchemy.ext.asyncio.AsyncSession:
        """セッションを取得する。"""
        sess = cls.session_var.get(None)
        if sess is None:
            raise RuntimeError(f"セッションが開始されていません。{cls.__qualname__}.start_session()を呼び出してください。")
        return sess

    @classmethod
    def select(cls) -> sqlalchemy.Select[tuple[typing.Self]]:
        """sqlalchemy.Selectを返す。"""
        # cls.count()などでfrom句が消えないように明示的にfrom句を指定して返す。
        return sqlalchemy.select(cls).select_from(cls)

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
    async def count(cls, query: sqlalchemy.Select | sqlalchemy.CompoundSelect) -> int:
        """queryのレコード数を取得する。"""
        # pylint: disable=not-callable
        return (
            await cls.scalar_one_or_none(
                sqlalchemy.select(sqlalchemy.func.count()).select_from(query.order_by(None).subquery())
            )
            or 0
        )

    @classmethod
    async def scalar_one(cls, query: sqlalchemy.Select[tuple[T]] | sqlalchemy.CompoundSelect[tuple[T]]) -> T:
        """queryの結果を1件取得する。

        Args:
            query: クエリ。

        Returns:
            1件のインスタンス。

        Raises:
            sqlalchemy.exc.NoResultFound: 結果が0件の場合。
            sqlalchemy.exc.MultipleResultsFound: 結果が複数件の場合。

        """
        return (await cls.session().execute(query)).scalar_one()

    @classmethod
    async def scalar_one_or_none(cls, query: sqlalchemy.Select[tuple[T]] | sqlalchemy.CompoundSelect[tuple[T]]) -> T | None:
        """queryの結果を0件または1件取得する。

        Args:
            query: クエリ。

        Returns:
            0件の場合はNone、1件の場合はインスタンス。

        Raises:
            sqlalchemy.exc.MultipleResultsFound: 結果が複数件の場合。

        """
        return (await cls.session().execute(query)).scalar_one_or_none()

    @classmethod
    async def scalars(cls, query: sqlalchemy.Select[tuple[T]] | sqlalchemy.CompoundSelect[tuple[T]]) -> list[T]:
        """queryの結果を全件取得する。

        Args:
            query: クエリ。

        Returns:
            全件のインスタンスのリスト。

        """
        return list((await cls.session().execute(query)).scalars().all())

    @classmethod
    async def one(cls, query: sqlalchemy.Select[TT] | sqlalchemy.CompoundSelect[TT]) -> sqlalchemy.Row[TT]:
        """queryの結果を1件取得する。

        Args:
            query: クエリ。

        Returns:
            1件のインスタンス。

        Raises:
            sqlalchemy.exc.NoResultFound: 結果が0件の場合。
            sqlalchemy.exc.MultipleResultsFound: 結果が複数件の場合。

        """
        return (await cls.session().execute(query)).one()

    @classmethod
    async def one_or_none(cls, query: sqlalchemy.Select[TT] | sqlalchemy.CompoundSelect[TT]) -> sqlalchemy.Row[TT] | None:
        """queryの結果を0件または1件取得する。

        Args:
            query: クエリ。

        Returns:
            0件の場合はNone、1件の場合はインスタンス。

        Raises:
            sqlalchemy.exc.MultipleResultsFound: 結果が複数件の場合。

        """
        return (await cls.session().execute(query)).one_or_none()

    @classmethod
    async def all(cls, query: sqlalchemy.Select[TT] | sqlalchemy.CompoundSelect[TT]) -> list[sqlalchemy.Row[TT]]:
        """queryの結果を全件取得する。

        Args:
            query: クエリ。

        Returns:
            全件のインスタンスのリスト。

        """
        return list((await cls.session().execute(query)).all())

    @classmethod
    async def get_by_id(cls, id_: int, for_update: bool = False) -> typing.Self | None:
        """IDを元にインスタンスを取得。

        Args:
            id_: ID。
            for_update: 更新ロックを取得するか否か。

        Returns:
            インスタンス。

        """
        q = cls.select().where(cls.id == id_)  # type: ignore  # pylint: disable=no-member
        if for_update:
            q = q.with_for_update()
        return await cls.scalar_one_or_none(q)  # type: ignore[arg-type]

    @classmethod
    async def paginate(
        cls,
        query: sqlalchemy.Select | sqlalchemy.CompoundSelect,
        page: int,
        per_page: int,
        scalar: bool = True,
    ) -> pytilpack._paginator.Paginator:
        """Flask-SQLAlchemy風ページネーション。

        Args:
            query: ページネーションするクエリ。
            page: ページ番号。
            per_page: 1ページあたりのアイテム数。
            scalar: Trueの場合、スカラー値を返す。Falseの場合、全件のインスタンスを返す。

        Returns:
            ページネーションされた結果を返すpytilpack._paginator.Paginatorインスタンス。
        """
        assert page > 0, "ページ番号は1以上でなければなりません。"
        assert per_page > 0, "1ページあたりのアイテム数は1以上でなければなりません。"
        total = await cls.count(query)
        page_query = query.offset((page - 1) * per_page).limit(per_page)
        items = await (cls.scalars(page_query) if scalar else cls.all(page_query))
        # pylint: disable=protected-access
        return pytilpack._paginator.Paginator(page=page, per_page=per_page, items=items, total=total)

    def to_dict(
        self,
        includes: list[str] | None = None,
        excludes: list[str] | None = None,
        exclude_none: bool = False,
        value_converter: typing.Callable[[typing.Any], typing.Any] | None = None,
        datetime_to_iso: bool = True,
    ) -> dict[str, typing.Any]:
        """インスタンスを辞書化する。

        Args:
            includes: 辞書化するフィールド名のリスト。excludesと同時指定不可。
            excludes: 辞書化しないフィールド名のリスト。includesと同時指定不可。
            exclude_none: Noneのフィールドを除外するかどうか。
            value_converter: 各フィールドの値を変換する関数。引数は値、戻り値は変換後の値。
            datetime_to_iso: datetime型の値をISOフォーマットの文字列に変換するかどうか。

        Returns:
            辞書。

        """
        assert (includes is None) or (excludes is None)
        mapper = sqlalchemy.inspect(self.__class__, raiseerr=True)
        assert mapper is not None
        all_columns = [
            mapper.get_property_by_column(column).key
            for column in self.__table__.columns  # type: ignore[attr-defined]
        ]
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

        def convert_value(value: typing.Any) -> typing.Any:
            """値を変換する関数。"""
            if datetime_to_iso and isinstance(value, datetime.datetime | datetime.date):
                return value.isoformat()
            if value_converter is not None:
                return value_converter(value)
            return value

        return {
            column_name: convert_value(getattr(self, column_name))
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
        if allow_id and isinstance(unique_id, int):
            q = cls.select().where(cls.id == unique_id)  # type: ignore
        else:
            q = cls.select().where(cls.unique_id == unique_id)  # type: ignore
        if for_update:
            q = q.with_for_update()
        return await cls.scalar_one_or_none(q)


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


async def asafe_close(session: sqlalchemy.ext.asyncio.AsyncSession, log_level: int | None = logging.DEBUG):
    """例外を出さずにセッションをクローズ。"""
    try:
        if session.is_active:
            await session.rollback()
        await session.close()
    except Exception:
        if log_level is not None:
            logger.log(log_level, "セッションクローズ失敗", exc_info=True)
