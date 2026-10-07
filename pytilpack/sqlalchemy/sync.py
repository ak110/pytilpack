"""SQLAlchemy用のユーティリティ集（同期版）。"""

import asyncio
import atexit
import contextlib
import contextvars
import functools
import logging
import threading
import time
import typing

import sqlalchemy
import sqlalchemy.engine
import sqlalchemy.orm
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


class SyncAsyncBridgeMixin:
    """同期DBを非同期環境から扱うためのブリッジMixin。

    SQLAlchemyの同期APIによるI/Oを`asyncio.to_thread`でスレッドに逃がし、
    awaitableなインターフェースを提供する。各呼び出しは別スレッド・独立セッション
    ・独立トランザクションで実行される。

    SyncMixinが継承する形で提供されるため、`SyncMixin.acount(...)`等の
    呼び出しはそのまま維持される。非同期専用のコードから同期DBを利用する場合の
    責務分離を明確にする目的で、別Mixinとして切り出している。
    """

    @classmethod
    async def acount(cls, query: sqlalchemy.Select | sqlalchemy.CompoundSelect) -> int:
        """queryのレコード数を返す。非同期版。"""
        # cls.count.__func__はSyncMixin側で定義されるためmypy向けに抑制する。
        sync_cls = typing.cast("type[SyncMixin]", cls)
        return await run_sync_with_session(sync_cls.count.__func__)(sync_cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def ascalar_one[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> T:
        """queryの結果を1件返す。非同期版。"""
        sync_cls = typing.cast("type[SyncMixin]", cls)
        return await run_sync_with_session(sync_cls.scalar_one.__func__)(sync_cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def ascalar_one_or_none[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> T | None:
        """queryの結果を0件または1件返す。非同期版。"""
        sync_cls = typing.cast("type[SyncMixin]", cls)
        return await run_sync_with_session(sync_cls.scalar_one_or_none.__func__)(sync_cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def ascalars[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> list[T]:
        """queryの結果を全件返す。非同期版。"""
        sync_cls = typing.cast("type[SyncMixin]", cls)
        return await run_sync_with_session(sync_cls.scalars.__func__)(sync_cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def aone[*Ts](cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]) -> sqlalchemy.Row[*Ts]:
        """queryの結果を1件返す。非同期版。"""
        sync_cls = typing.cast("type[SyncMixin]", cls)
        return await run_sync_with_session(sync_cls.one.__func__)(sync_cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def aone_or_none[*Ts](
        cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]
    ) -> sqlalchemy.Row[*Ts] | None:
        """queryの結果を0件または1件返す。非同期版。"""
        sync_cls = typing.cast("type[SyncMixin]", cls)
        return await run_sync_with_session(sync_cls.one_or_none.__func__)(sync_cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def aall[*Ts](cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]) -> list[sqlalchemy.Row[*Ts]]:
        """queryの結果を全件返す。非同期版。"""
        sync_cls = typing.cast("type[SyncMixin]", cls)
        return await run_sync_with_session(sync_cls.all.__func__)(sync_cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def aget_by_id(cls, id_: int, for_update: bool = False) -> typing.Self | None:
        """IDを元にインスタンスを取得する。非同期版。"""
        sync_cls = typing.cast("type[SyncMixin]", cls)
        return await run_sync_with_session(sync_cls.get_by_id.__func__)(sync_cls, id_, for_update)  # type: ignore[attr-defined,return-value]

    @classmethod
    async def apaginate(
        cls,
        query: sqlalchemy.Select | sqlalchemy.CompoundSelect,
        page: int,
        per_page: int,
        scalar: bool = True,
    ) -> pytilpack.paginator.Paginator:
        """Flask-SQLAlchemy風ページネーションを返す。非同期版。"""
        sync_cls = typing.cast("type[SyncMixin]", cls)
        return await run_sync_with_session(sync_cls.paginate.__func__)(sync_cls, query, page, per_page, scalar)  # type: ignore[attr-defined]


class SyncMixin(_QueryMixin, _ReprMixin, _ToDictMixin, SyncAsyncBridgeMixin):
    """モデルのベースクラス。SQLAlchemy 2.0スタイル・同期前提。

    Examples:
        モデル定義例::

            class Base(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy.SyncMixin):
                pass

            class User(Base):
                __tablename__ = "users"
                ...

        Quart例::

            @app.before_request
            async def _before_request() -> None:
                quart.g.db_session_token = models.Base.start_session()

            @app.teardown_request
            async def _teardown_request(_: BaseException | None) -> None:
                if hasattr(quart.g, "db_session_token"):
                    models.Base.close_session(quart.g.db_session_token)
                    del quart.g.db_session_token

    """

    engine: sqlalchemy.Engine | None = None
    """DB接続。"""

    sessionmaker: sqlalchemy.orm.sessionmaker[sqlalchemy.orm.Session] | None = None
    """セッションファクトリ。"""

    session_var: contextvars.ContextVar[sqlalchemy.orm.Session] = contextvars.ContextVar("session_var")
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
        **kwargs: typing.Any,
    ) -> None:
        """DB接続を初期化する。

        Args:
            url: DB接続URL。
            pool_size: コネクションプールのサイズ。スレッド数に応じて調整要。
            max_overflow: コネクションプールの最大オーバーフロー数。Noneの場合はデフォルト値を使用。
            pool_recycle: コネクションプールのリサイクル時間。Noneの場合はデフォルト値を使用。
            pool_pre_ping: コネクションプールのプレピン。Noneの場合はデフォルト値を使用。
            autoflush: セッションのautoflushフラグ。デフォルトはTrue。
            expire_on_commit: セッションのexpire_on_commitフラグ。デフォルトはFalse。
            **kwargs: sqlalchemy.create_engineに渡す追加のキーワード引数。

        """
        if cls.engine is not None:
            raise RuntimeError("DB接続はすでに初期化されています。")

        engine_kwargs = _engine_kwargs(kwargs, pool_size, max_overflow, pool_recycle, pool_pre_ping)
        cls.engine = sqlalchemy.create_engine(url, **engine_kwargs)
        atexit.register(cls.engine.dispose)

        cls.sessionmaker = sqlalchemy.orm.sessionmaker(cls.engine, autoflush=autoflush, expire_on_commit=expire_on_commit)

    @classmethod
    def connect(cls) -> sqlalchemy.Connection:
        """DBに接続する。

        使用例::
            with Base.connect() as conn:
                Base.metadata.create_all(conn)

        """
        if cls.engine is None:
            raise RuntimeError("init()が呼ばれていません。")
        return cls.engine.connect()

    @classmethod
    @contextlib.contextmanager
    def session_scope(
        cls,
        name: str | None = None,
        log_level: int = logging.DEBUG,
    ) -> typing.Generator[sqlalchemy.orm.Session, None, None]:
        """セッションを開始するコンテキストマネージャ。

        使用例::
            with Base.session_scope() as session:
                ...

        Args:
            name: セッション名。指定時のみログ出力する。
            log_level: ログレベル。

        """
        if cls.sessionmaker is None:
            raise RuntimeError("init()が呼ばれていません。")
        token = cls.start_session(name=name, log_level=log_level)
        try:
            yield cls.session()
        finally:
            cls.close_session(token, name=name, log_level=log_level)

    @classmethod
    @contextlib.asynccontextmanager
    async def asession_scope(
        cls,
        name: str | None = None,
        log_level: int = logging.DEBUG,
    ) -> typing.AsyncGenerator[sqlalchemy.orm.Session, None]:
        """セッションを開始するコンテキストマネージャ。

        使用例::
            async with Base.asession_scope() as session:
                ...

        Args:
            name: セッション名。指定時のみログ出力する。
            log_level: ログレベル。

        """
        if cls.sessionmaker is None:
            raise RuntimeError("init()が呼ばれていません。")
        token = cls.start_session(name=name, log_level=log_level)
        try:
            yield cls.session()
        finally:
            cls.close_session(token, name=name, log_level=log_level)

    @classmethod
    def start_session(
        cls, name: str | None = None, log_level: int = logging.DEBUG
    ) -> contextvars.Token[sqlalchemy.orm.Session]:
        """セッションを開始する。"""
        if cls.sessionmaker is None:
            raise RuntimeError("init()が呼ばれていません。")
        # arid: disable
        # async版（pytilpack.sqlalchemy.async_.AsyncMixin.start_session）と並行実装のため許容する。
        session = cls.sessionmaker()  # pylint: disable=not-callable
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
    def close_session(
        cls, token: contextvars.Token[sqlalchemy.orm.Session], name: str | None = None, log_level: int = logging.DEBUG
    ) -> None:
        """セッションを終了する。"""
        # arid: disable
        # async版（pytilpack.sqlalchemy.async_.AsyncMixin.close_session）と並行実装のため許容する。
        session = cls.session()
        if name is not None:
            logger.log(
                log_level,
                f"セッション終了: {name} session={id(session):x},"
                f" thread={threading.get_ident():x},"
                f" task={pytilpack.asyncio.get_task_id_hex()}",
            )
        safe_close(session)
        cls.session_var.reset(token)
        # arid: enable

    # arid: disable
    # async版（pytilpack.sqlalchemy.async_.AsyncMixin）と並行実装のため許容する。
    @classmethod
    def session(cls) -> sqlalchemy.orm.Session:
        """セッションを取得する。"""
        sess = cls.session_var.get(None)
        if sess is None:
            raise RuntimeError(f"セッションが開始されていません。{cls.__qualname__}.start_session()を呼び出してください。")
        return sess

    # arid: enable

    @classmethod
    def count(cls, query: sqlalchemy.Select | sqlalchemy.CompoundSelect) -> int:
        """queryのレコード数を取得する。"""
        # pylint: disable=not-callable
        return cls.scalar_one_or_none(_count_query(query)) or 0

    @classmethod
    def scalar_one[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> T:
        """queryの結果を1件取得する。

        Args:
            query: クエリ。

        Returns:
            1件のインスタンス。

        Raises:
            sqlalchemy.exc.NoResultFound: 結果が0件の場合。
            sqlalchemy.exc.MultipleResultsFound: 結果が複数件の場合。

        """
        return cls.session().execute(query).scalar_one()

    @classmethod
    def scalar_one_or_none[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> T | None:
        """queryの結果を0件または1件取得する。

        Args:
            query: クエリ。

        Returns:
            0件の場合はNone、1件の場合はインスタンス。

        Raises:
            sqlalchemy.exc.MultipleResultsFound: 結果が複数件の場合。

        """
        return cls.session().execute(query).scalar_one_or_none()

    @classmethod
    def scalars[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> list[T]:
        """queryの結果を全件取得する。

        Args:
            query: クエリ。

        Returns:
            全件のインスタンスのリスト。

        """
        return list(cls.session().execute(query).scalars().all())

    @classmethod
    def one[*Ts](cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]) -> sqlalchemy.Row[*Ts]:
        """queryの結果を1件取得する。

        Args:
            query: クエリ。

        Returns:
            1件のインスタンス。

        Raises:
            sqlalchemy.exc.NoResultFound: 結果が0件の場合。
            sqlalchemy.exc.MultipleResultsFound: 結果が複数件の場合。

        """
        return cls.session().execute(query).one()

    @classmethod
    def one_or_none[*Ts](cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]) -> sqlalchemy.Row[*Ts] | None:
        """queryの結果を0件または1件取得する。

        Args:
            query: クエリ。

        Returns:
            0件の場合はNone、1件の場合はインスタンス。

        Raises:
            sqlalchemy.exc.MultipleResultsFound: 結果が複数件の場合。

        """
        return cls.session().execute(query).one_or_none()

    @classmethod
    def all[*Ts](cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]) -> list[sqlalchemy.Row[*Ts]]:
        """queryの結果を全件取得する。

        Args:
            query: クエリ。

        Returns:
            全件のインスタンスのリスト。

        """
        return list(cls.session().execute(query).all())

    @classmethod
    def get_by_id_not_null(
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
        instance = cls.get_by_id(id_, for_update=for_update, options=options)
        return _require_instance(instance, cls, id_)

    @classmethod
    def get_by_id(
        cls, id_: int, for_update: bool = False, options: sqlalchemy.sql.base.ExecutableOption | None = None
    ) -> typing.Self | None:
        """IDを元にインスタンスを取得。

        Args:
            id_: ID。
            for_update: 更新ロックを取得するか否か。
            options: クエリオプション。eager loadingなどに使用。

        Returns:
            インスタンス。

        """
        q = cls.select().where(_id_filter(cls, id_))  # type: ignore  # pylint: disable=no-member
        q = _query_options(q, for_update, options)
        return cls.scalar_one_or_none(q)

    @classmethod
    def paginate(
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
        total = cls.count(query)
        items = cls.scalars(page_query) if scalar else cls.all(page_query)
        # pylint: disable=protected-access
        return pytilpack.paginator.Paginator(page=page, per_page=per_page, items=items, total=total)

    @classmethod
    def commit(cls) -> None:
        """セッションをコミットする。"""
        cls.session().commit()


class SyncUniqueIDMixin(_UniqueIDMixin):
    """self.unique_idを持つテーブルクラスにユニークID操作メソッドを付与するmixin。"""

    @classmethod
    def get_by_unique_id(
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
        assert issubclass(cls, SyncMixin)
        q = cls.select().where(_id_filter(cls, unique_id, not (allow_id and isinstance(unique_id, int))))
        q = _query_options(q, for_update)
        return cls.scalar_one_or_none(q)


def wait_for_connection(url: str, timeout: float = 180.0) -> None:
    """DBに接続可能になるまで待機する。"""
    state = _WaitForConnectionState(url, timeout)
    while True:
        try:
            engine = sqlalchemy.create_engine(url)
            try:
                with engine.connect() as connection:
                    result = connection.execute(sqlalchemy.text("SELECT 1"))
                    result.close()
            finally:
                engine.dispose()
            state.on_success()
            break
        except Exception as e:
            time.sleep(state.on_failure(e))


def safe_close(
    session: sqlalchemy.orm.Session | sqlalchemy.orm.scoped_session,
    log_level: int | None = logging.DEBUG,
):
    """例外を送出せずにセッションをクローズ。"""
    try:
        session.close()
    except Exception:
        if log_level is not None:
            logger.log(log_level, "セッションクローズ失敗", exc_info=True)


def run_sync_with_session[**P, R](
    func: "typing.Callable[typing.Concatenate[type[SyncMixin], P], R]",
) -> "typing.Callable[typing.Concatenate[type[SyncMixin], P], typing.Awaitable[R]]":
    """同期関数を非同期に実行し、スレッド内でセッションを管理するデコレーター。

    別スレッドで実行される関数内で自動的にセッションスコープを作成する。
    各呼び出しは独立したセッション・トランザクションを持つ。

    Args:
        func: デコレート対象の同期関数

    Returns:
        非同期版の関数
    """

    @functools.wraps(func)
    async def wrapper(cls: type[SyncMixin], *args: P.args, **kwargs: P.kwargs) -> R:
        def _impl() -> R:
            with cls.session_scope() as session:
                result = func(cls, *args, **kwargs)
                session.commit()
                return result

        return await asyncio.to_thread(_impl)

    return wrapper
