__lazy_modules__ = [
    "asyncio",
    "atexit",
    "contextlib",
    "contextvars",
    "functools",
    "logging",
    "pytilpack.asyncio",
    "pytilpack.paginator",
    "pytilpack.sqlalchemy._base",
    "sqlalchemy",
    "sqlalchemy.engine",
    "sqlalchemy.orm",
    "sqlalchemy.sql.base",
    "threading",
    "time",
    "typing",
]

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
    @classmethod
    async def acount(cls, query: sqlalchemy.Select | sqlalchemy.CompoundSelect) -> int:
        sync_cls = typing.cast("type[SyncMixin]", cls)
        return await run_sync_with_session(sync_cls.count.__func__)(sync_cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def ascalar_one[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> T:
        sync_cls = typing.cast("type[SyncMixin]", cls)
        return await run_sync_with_session(sync_cls.scalar_one.__func__)(sync_cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def ascalar_one_or_none[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> T | None:
        sync_cls = typing.cast("type[SyncMixin]", cls)
        return await run_sync_with_session(sync_cls.scalar_one_or_none.__func__)(sync_cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def ascalars[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> list[T]:
        sync_cls = typing.cast("type[SyncMixin]", cls)
        return await run_sync_with_session(sync_cls.scalars.__func__)(sync_cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def aone[*Ts](cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]) -> sqlalchemy.Row[*Ts]:
        sync_cls = typing.cast("type[SyncMixin]", cls)
        return await run_sync_with_session(sync_cls.one.__func__)(sync_cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def aone_or_none[*Ts](
        cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]
    ) -> sqlalchemy.Row[*Ts] | None:
        sync_cls = typing.cast("type[SyncMixin]", cls)
        return await run_sync_with_session(sync_cls.one_or_none.__func__)(sync_cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def aall[*Ts](cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]) -> list[sqlalchemy.Row[*Ts]]:
        sync_cls = typing.cast("type[SyncMixin]", cls)
        return await run_sync_with_session(sync_cls.all.__func__)(sync_cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def aget_by_id(cls, id_: int, for_update: bool = False) -> typing.Self | None:
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
        sync_cls = typing.cast("type[SyncMixin]", cls)
        return await run_sync_with_session(sync_cls.paginate.__func__)(sync_cls, query, page, per_page, scalar)  # type: ignore[attr-defined]


class SyncMixin(_QueryMixin, _ReprMixin, _ToDictMixin, SyncAsyncBridgeMixin):
    engine: sqlalchemy.Engine | None = None

    sessionmaker: sqlalchemy.orm.sessionmaker[sqlalchemy.orm.Session] | None = None

    session_var: contextvars.ContextVar[sqlalchemy.orm.Session] = contextvars.ContextVar("session_var")

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
        if cls.engine is not None:
            raise RuntimeError(
                f"DB接続はすでに初期化されています。{cls.__qualname__}.init()はクラスごとに1回だけ呼び、"
                "初期化済みの接続をそのまま使う（term()の後も再初期化はできない）"
            )

        engine_kwargs = _engine_kwargs(kwargs, pool_size, max_overflow, pool_recycle, pool_pre_ping)
        cls.engine = sqlalchemy.create_engine(url, **engine_kwargs)
        atexit.register(cls.engine.dispose)

        cls.sessionmaker = sqlalchemy.orm.sessionmaker(cls.engine, autoflush=autoflush, expire_on_commit=expire_on_commit)

    @classmethod
    def connect(cls) -> sqlalchemy.Connection:
        if cls.engine is None:
            raise RuntimeError(f"init()が呼ばれていません。先に{cls.__qualname__}.init()でDB接続を初期化する")
        return cls.engine.connect()

    @classmethod
    @contextlib.contextmanager
    def session_scope(
        cls,
        name: str | None = None,
        log_level: int = logging.DEBUG,
    ) -> typing.Generator[sqlalchemy.orm.Session, None, None]:
        if cls.sessionmaker is None:
            raise RuntimeError(f"init()が呼ばれていません。先に{cls.__qualname__}.init()でDB接続を初期化する")
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
        if cls.sessionmaker is None:
            raise RuntimeError(f"init()が呼ばれていません。先に{cls.__qualname__}.init()でDB接続を初期化する")
        token = cls.start_session(name=name, log_level=log_level)
        try:
            yield cls.session()
        finally:
            cls.close_session(token, name=name, log_level=log_level)

    @classmethod
    def start_session(
        cls, name: str | None = None, log_level: int = logging.DEBUG
    ) -> contextvars.Token[sqlalchemy.orm.Session]:
        if cls.sessionmaker is None:
            raise RuntimeError(f"init()が呼ばれていません。先に{cls.__qualname__}.init()でDB接続を初期化する")
        # arid: disable
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
        # arid: disable
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
    @classmethod
    def session(cls) -> sqlalchemy.orm.Session:
        sess = cls.session_var.get(None)
        if sess is None:
            raise RuntimeError(f"セッションが開始されていません。{cls.__qualname__}.start_session()を呼び出してください。")
        return sess

    # arid: enable

    @classmethod
    def count(cls, query: sqlalchemy.Select | sqlalchemy.CompoundSelect) -> int:
        # pylint: disable=not-callable
        return cls.scalar_one_or_none(_count_query(query)) or 0

    @classmethod
    def scalar_one[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> T:
        return cls.session().execute(query).scalar_one()

    @classmethod
    def scalar_one_or_none[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> T | None:
        return cls.session().execute(query).scalar_one_or_none()

    @classmethod
    def scalars[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> list[T]:
        return list(cls.session().execute(query).scalars().all())

    @classmethod
    def one[*Ts](cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]) -> sqlalchemy.Row[*Ts]:
        return cls.session().execute(query).one()

    @classmethod
    def one_or_none[*Ts](cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]) -> sqlalchemy.Row[*Ts] | None:
        return cls.session().execute(query).one_or_none()

    @classmethod
    def all[*Ts](cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]) -> list[sqlalchemy.Row[*Ts]]:
        return list(cls.session().execute(query).all())

    @classmethod
    def get_by_id_not_null(
        cls, id_: int, for_update: bool = False, options: sqlalchemy.sql.base.ExecutableOption | None = None
    ) -> typing.Self:
        instance = cls.get_by_id(id_, for_update=for_update, options=options)
        return _require_instance(instance, cls, id_)

    @classmethod
    def get_by_id(
        cls, id_: int, for_update: bool = False, options: sqlalchemy.sql.base.ExecutableOption | None = None
    ) -> typing.Self | None:
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
        page_query = _page_query(query, page, per_page)
        total = cls.count(query)
        items = cls.scalars(page_query) if scalar else cls.all(page_query)
        # pylint: disable=protected-access
        return pytilpack.paginator.Paginator(page=page, per_page=per_page, items=items, total=total)

    @classmethod
    def commit(cls) -> None:
        cls.session().commit()


class SyncUniqueIDMixin(_UniqueIDMixin):
    @classmethod
    def get_by_unique_id(
        cls: type[typing.Self],
        unique_id: str | int,
        allow_id: bool = False,
        for_update: bool = False,
    ) -> typing.Self | None:
        assert issubclass(cls, SyncMixin)
        q = cls.select().where(_id_filter(cls, unique_id, not (allow_id and isinstance(unique_id, int))))
        q = _query_options(q, for_update)
        return cls.scalar_one_or_none(q)


def wait_for_connection(url: str, timeout: float = 180.0) -> None:
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
    try:
        session.close()
    except Exception:
        if log_level is not None:
            logger.log(log_level, "セッションクローズ失敗", exc_info=True)


def run_sync_with_session[**P, R](
    func: "typing.Callable[typing.Concatenate[type[SyncMixin], P], R]",
) -> "typing.Callable[typing.Concatenate[type[SyncMixin], P], typing.Awaitable[R]]":

    @functools.wraps(func)
    async def wrapper(cls: type[SyncMixin], *args: P.args, **kwargs: P.kwargs) -> R:
        def _impl() -> R:
            with cls.session_scope() as session:
                result = func(cls, *args, **kwargs)
                session.commit()
                return result

        return await asyncio.to_thread(_impl)

    return wrapper
