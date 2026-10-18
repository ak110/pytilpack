"""SQLAlchemy用のユーティリティ集（async版）。"""

__lazy_modules__ = [
    "asyncio",
    "contextlib",
    "contextvars",
    "dataclasses",
    "logging",
    "pytilpack.asyncio",
    "pytilpack.paginator",
    "pytilpack.sqlalchemy._base",
    "sqlalchemy",
    "sqlalchemy.ext.asyncio",
    "sqlalchemy.sql.base",
    "threading",
    "typing",
]

import asyncio
import contextlib
import contextvars
import dataclasses
import logging
import threading
import typing

import sqlalchemy
import sqlalchemy.ext.asyncio
import sqlalchemy.sql.base

import pytilpack.asyncio
import pytilpack.paginator
from pytilpack.sqlalchemy._base import (
    _count_query,
    _engine_kwargs,
    _id_filter,
    _page_query,
    _query_options,
    _QueryMixin,
    _ReprMixin,
    _require_instance,
    _ToDictMixin,
    _UniqueIDMixin,
    _WaitForConnectionState,
)

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class _InitArgs:
    """init()の引数。"""

    url: str | sqlalchemy.engine.URL
    autoflush: bool
    expire_on_commit: bool
    engine_kwargs: dict


class AsyncMixin(_QueryMixin, sqlalchemy.ext.asyncio.AsyncAttrs, _ReprMixin, _ToDictMixin):
    """モデルのベースクラス。SQLAlchemy 2.0スタイル・async前提。

    Examples:
        モデル定義例::

            class Base(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy.AsyncMixin):
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

    _init_args: _InitArgs | None = None
    """初期化引数。init()呼び出し後に設定される。"""

    _thread_local: threading.local | None = None
    """スレッドローカルストレージ。init()呼び出し後に設定される。"""

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
        eagerly_init: bool = True,
        **kwargs: typing.Any,
    ) -> None:
        """DB接続を初期化する。

        engineとsessionmakerはスレッドローカルで遅延初期化される。
        各スレッドが初めてDB操作を行う際にそのスレッド専用のengineとsessionmakerが生成される。

        Args:
            url: DB接続URL。
            pool_size: コネクションプールのサイズ。スレッド数に応じて調整要。負数の場合はプーリングを無効化する。
            max_overflow: コネクションプールの最大オーバーフロー数。Noneの場合はデフォルト値を使用。
            pool_recycle: コネクションプールのリサイクル時間。Noneの場合はデフォルト値を使用。
            pool_pre_ping: コネクションプールのプレピン。Noneの場合はデフォルト値を使用。
            autoflush: セッションのautoflushフラグ。デフォルトはTrue。
            expire_on_commit: セッションのexpire_on_commitフラグ。デフォルトはFalse。
            eagerly_init: Trueの場合（デフォルト）、呼び出し元スレッドのengineとsessionmakerをすぐに生成する。
            **kwargs: sqlalchemy.ext.asyncio.create_async_engine()へのキーワード引数。

        """
        if cls._init_args is not None:
            raise RuntimeError(
                f"DB接続はすでに初期化されています。{cls.__qualname__}.init()はクラスごとに1回だけ呼び、"
                "初期化済みの接続をそのまま使う（term()の後も再初期化はできない）"
            )

        engine_kwargs = _engine_kwargs(
            kwargs,
            pool_size,
            max_overflow,
            pool_recycle,
            pool_pre_ping,
            disable_pool=pool_size is not None and pool_size < 0,
        )

        cls._init_args = _InitArgs(
            url=url,
            autoflush=autoflush,
            expire_on_commit=expire_on_commit,
            engine_kwargs=engine_kwargs,
        )
        cls._thread_local = threading.local()

        if eagerly_init:
            cls._get_engine_and_sessionmaker()

    @classmethod
    async def term(cls) -> None:
        """現在のスレッドのDB接続を終了する。

        スレッドローカルなengineを`dispose()`し、engineとsessionmakerの参照を`None`へ戻す。
        スレッド終了時やテスト後の後始末に使用する。

        init()で設定したクラス単位の初期化状態は保持するため、term()の後にinit()を
        呼び直すことはできない（init()は二重呼び出しをRuntimeErrorで拒否する）。

        """
        if cls._init_args is None:
            logger.warning(f"未初期化時のterm()呼び出し。{cls.__qualname__}.init()前のため何もせずに戻った（対応不要）")
            return
        if cls._thread_local is None:
            return
        if hasattr(cls._thread_local, "engine") and cls._thread_local.engine is not None:
            await cls._thread_local.engine.dispose()
            cls._thread_local.engine = None
            cls._thread_local.sessionmaker = None

    @classmethod
    def _get_engine_and_sessionmaker(
        cls,
    ) -> tuple[
        sqlalchemy.ext.asyncio.AsyncEngine,
        sqlalchemy.ext.asyncio.async_sessionmaker[sqlalchemy.ext.asyncio.AsyncSession],
    ]:
        """現在のスレッドのengineとsessionmakerを取得する（なければ遅延生成）。"""
        if cls._init_args is None:
            raise RuntimeError(f"init()が呼ばれていません。先に{cls.__qualname__}.init()でDB接続を初期化する")
        if cls._thread_local is None:
            raise RuntimeError(f"init()が呼ばれていません。先に{cls.__qualname__}.init()でDB接続を初期化する")
        if not hasattr(cls._thread_local, "engine") or cls._thread_local.engine is None:
            cls._thread_local.engine = sqlalchemy.ext.asyncio.create_async_engine(
                cls._init_args.url, **cls._init_args.engine_kwargs
            )
            cls._thread_local.sessionmaker = sqlalchemy.ext.asyncio.async_sessionmaker(
                cls._thread_local.engine,
                autoflush=cls._init_args.autoflush,
                expire_on_commit=cls._init_args.expire_on_commit,
            )
        return cls._thread_local.engine, cls._thread_local.sessionmaker

    @classmethod
    def engine(cls) -> sqlalchemy.ext.asyncio.AsyncEngine:
        """現在のスレッドのDB接続を返す。init()後に初めて呼ばれた時点で遅延生成される。"""
        return cls._get_engine_and_sessionmaker()[0]

    @classmethod
    def sessionmaker(
        cls,
    ) -> sqlalchemy.ext.asyncio.async_sessionmaker[sqlalchemy.ext.asyncio.AsyncSession]:
        """現在のスレッドのセッションファクトリを返す。init()後に初めて呼ばれた時点で遅延生成される。"""
        return cls._get_engine_and_sessionmaker()[1]

    @classmethod
    def connect(cls) -> sqlalchemy.ext.asyncio.AsyncConnection:
        """DBに接続する。

        使用例::
            async with Base.connect() as conn:
                await conn.run_sync(Base.metadata.create_all)

        """
        return cls.engine().connect()

    @classmethod
    @contextlib.asynccontextmanager
    async def session_scope(
        cls,
        name: str | None = None,
        log_level: int = logging.DEBUG,
    ):
        """セッションを開始するコンテキストマネージャ。

        使用例::
            async with Base.session_scope() as session:
                ...

        Args:
            name: セッション名。指定時のみログ出力する。
            log_level: ログレベル。

        """
        token = await cls.start_session(name=name, log_level=log_level)
        try:
            yield cls.session()
        finally:
            await cls.close_session(token, name=name, log_level=log_level)

    @classmethod
    async def start_session(
        cls, name: str | None = None, log_level: int = logging.DEBUG
    ) -> contextvars.Token[sqlalchemy.ext.asyncio.AsyncSession]:
        """セッションを開始する。"""
        # arid: disable
        # sync版（pytilpack.sqlalchemy.sync.SyncMixin.start_session）と並行実装のため許容する。
        session = cls.sessionmaker()()  # pylint: disable=not-callable
        token = cls.session_var.set(session)
        if name is not None:
            logger.log(
                log_level,
                f"セッション開始: {name} session={id(session):x},"
                f" thread={threading.get_ident():x},"
                f" task={pytilpack.asyncio.get_task_id_hex()}",
            )
        return token
        # arid: enable

    @classmethod
    async def close_session(
        cls,
        token: contextvars.Token[sqlalchemy.ext.asyncio.AsyncSession],
        name: str | None = None,
        log_level: int = logging.DEBUG,
    ) -> None:
        """セッションを終了する。"""
        # arid: disable
        # sync版（pytilpack.sqlalchemy.sync.SyncMixin.close_session）と並行実装のため許容する。
        session = cls.session()
        if name is not None:
            logger.log(
                log_level,
                f"セッション終了: {name} session={id(session):x},"
                f" thread={threading.get_ident():x},"
                f" task={pytilpack.asyncio.get_task_id_hex()}",
            )
        await asafe_close(session)
        cls.session_var.reset(token)
        # arid: enable

    # arid: disable
    # sync版（pytilpack.sqlalchemy.sync.SyncMixin）と並行実装のため許容する。
    @classmethod
    def session(cls) -> sqlalchemy.ext.asyncio.AsyncSession:
        """セッションを取得する。"""
        sess = cls.session_var.get(None)
        if sess is None:
            raise RuntimeError(f"セッションが開始されていません。{cls.__qualname__}.start_session()を呼び出してください。")
        return sess

    # arid: enable

    @classmethod
    async def count(cls, query: sqlalchemy.Select | sqlalchemy.CompoundSelect) -> int:
        """queryのレコード数を取得する。"""
        # pylint: disable=not-callable
        return await cls.scalar_one_or_none(_count_query(query)) or 0

    @classmethod
    async def scalar_one[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> T:
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
    async def scalar_one_or_none[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> T | None:
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
    async def scalars[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> list[T]:
        """queryの結果を全件取得する。

        Args:
            query: クエリ。

        Returns:
            全件のインスタンスのリスト。

        """
        return list((await cls.session().execute(query)).scalars().all())

    @classmethod
    async def one[*Ts](cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]) -> sqlalchemy.Row[*Ts]:
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
    async def one_or_none[*Ts](
        cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]
    ) -> sqlalchemy.Row[*Ts] | None:
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
    async def all[*Ts](cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]) -> list[sqlalchemy.Row[*Ts]]:
        """queryの結果を全件取得する。

        Args:
            query: クエリ。

        Returns:
            全件のインスタンスのリスト。

        """
        return list((await cls.session().execute(query)).all())

    @classmethod
    async def get_by_id_not_null(
        cls, id_: int, for_update: bool = False, options: sqlalchemy.sql.base.ExecutableOption | None = None
    ) -> typing.Self:
        """IDを元にインスタンスを取得。見つからない場合は例外を送出する。

        Args:
            id_: ID。
            for_update: 更新ロックを取得するか否か。
            options: クエリオプション。eager loadingなどに使用する。

        Returns:
            インスタンス。
        Raises:
            ValueError: 見つからない場合。
        """
        instance = await cls.get_by_id(id_, for_update=for_update, options=options)
        return _require_instance(instance, cls, id_)

    @classmethod
    async def get_by_id(
        cls, id_: int, for_update: bool = False, options: sqlalchemy.sql.base.ExecutableOption | None = None
    ) -> typing.Self | None:
        """IDを元にインスタンスを取得。

        Args:
            id_: ID。
            for_update: 更新ロックを取得するか否か。
            options: クエリオプション。eager loadingなどに使用する。

        Returns:
            インスタンス。

        """
        q = cls.select().where(_id_filter(cls, id_))  # type: ignore  # pylint: disable=no-member
        q = _query_options(q, for_update, options)
        return await cls.scalar_one_or_none(q)  # type: ignore[arg-type]

    @classmethod
    async def paginate(
        cls,
        query: sqlalchemy.Select | sqlalchemy.CompoundSelect,
        page: int,
        per_page: int,
        scalar: bool = True,
    ) -> pytilpack.paginator.Paginator:
        """Flask-SQLAlchemy風ページネーション。

        Args:
            query: ページネーションするクエリ。
            page: ページ番号。
            per_page: 1ページあたりのアイテム数。
            scalar: Trueの場合、スカラー値を返す。Falseの場合、全件のインスタンスを返す。

        Returns:
            ページネーションされた結果を返すpytilpack.paginator.Paginatorインスタンス。
        """
        page_query = _page_query(query, page, per_page)
        total = await cls.count(query)
        items = await (cls.scalars(page_query) if scalar else cls.all(page_query))
        # pylint: disable=protected-access
        return pytilpack.paginator.Paginator(page=page, per_page=per_page, items=items, total=total)

    @classmethod
    def run_with_session[**P, R](cls, func: typing.Callable[P, typing.Awaitable[R]], *args: P.args, **kwargs: P.kwargs) -> R:
        """非同期関数をセッション付きで同期実行する関数。

        Args:
            func: デコレート対象の非同期関数
            *args: 非同期関数への引数
            **kwargs: 非同期関数へのキーワード引数

        Returns:
            非同期関数の戻り値
        """

        async def wrapper() -> R:
            async with cls.session_scope():
                return await func(*args, **kwargs)

        return pytilpack.asyncio.run(wrapper())


class AsyncUniqueIDMixin(_UniqueIDMixin):
    """self.unique_idを持つテーブルクラスにユニークID操作メソッドを付与するmixin。"""

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
        q = cls.select().where(_id_filter(cls, unique_id, not (allow_id and isinstance(unique_id, int))))
        q = _query_options(q, for_update)
        return await cls.scalar_one_or_none(q)


async def await_for_connection(url: str, timeout: float = 180.0) -> None:
    """DBに接続可能になるまで待機する。"""
    state = _WaitForConnectionState(url, timeout)
    while True:
        try:
            engine = sqlalchemy.ext.asyncio.create_async_engine(url)
            try:
                async with engine.connect() as connection:
                    await connection.execute(sqlalchemy.text("SELECT 1"))
            finally:
                await engine.dispose()
            state.on_success()
            break
        except Exception as e:
            await asyncio.sleep(state.on_failure(e))


async def asafe_close(session: sqlalchemy.ext.asyncio.AsyncSession, log_level: int | None = logging.DEBUG):
    """例外を送出せずにセッションをクローズ。"""
    try:
        await asyncio.shield(session.close())
    except Exception:
        if log_level is not None:
            logger.log(log_level, "セッションクローズ失敗", exc_info=True)
