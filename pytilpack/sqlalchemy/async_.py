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
    url: str | sqlalchemy.engine.URL
    autoflush: bool
    expire_on_commit: bool
    engine_kwargs: dict


class AsyncMixin(_QueryMixin, sqlalchemy.ext.asyncio.AsyncAttrs, _ReprMixin, _ToDictMixin):
    _init_args: _InitArgs | None = None

    _thread_local: threading.local | None = None

    session_var: contextvars.ContextVar[sqlalchemy.ext.asyncio.AsyncSession] = contextvars.ContextVar("session_var")

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
        return cls._get_engine_and_sessionmaker()[0]

    @classmethod
    def sessionmaker(
        cls,
    ) -> sqlalchemy.ext.asyncio.async_sessionmaker[sqlalchemy.ext.asyncio.AsyncSession]:
        return cls._get_engine_and_sessionmaker()[1]

    @classmethod
    def connect(cls) -> sqlalchemy.ext.asyncio.AsyncConnection:
        return cls.engine().connect()

    @classmethod
    @contextlib.asynccontextmanager
    async def session_scope(
        cls,
        name: str | None = None,
        log_level: int = logging.DEBUG,
    ):
        token = await cls.start_session(name=name, log_level=log_level)
        try:
            yield cls.session()
        finally:
            await cls.close_session(token, name=name, log_level=log_level)

    @classmethod
    async def start_session(
        cls, name: str | None = None, log_level: int = logging.DEBUG
    ) -> contextvars.Token[sqlalchemy.ext.asyncio.AsyncSession]:
        # arid: disable
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
        # arid: disable
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
    @classmethod
    def session(cls) -> sqlalchemy.ext.asyncio.AsyncSession:
        sess = cls.session_var.get(None)
        if sess is None:
            raise RuntimeError(f"セッションが開始されていません。{cls.__qualname__}.start_session()を呼び出してください。")
        return sess

    # arid: enable

    @classmethod
    async def count(cls, query: sqlalchemy.Select | sqlalchemy.CompoundSelect) -> int:
        # pylint: disable=not-callable
        return await cls.scalar_one_or_none(_count_query(query)) or 0

    @classmethod
    async def scalar_one[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> T:
        return (await cls.session().execute(query)).scalar_one()

    @classmethod
    async def scalar_one_or_none[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> T | None:
        return (await cls.session().execute(query)).scalar_one_or_none()

    @classmethod
    async def scalars[T](cls, query: sqlalchemy.Select[T] | sqlalchemy.CompoundSelect[T]) -> list[T]:
        return list((await cls.session().execute(query)).scalars().all())

    @classmethod
    async def one[*Ts](cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]) -> sqlalchemy.Row[*Ts]:
        return (await cls.session().execute(query)).one()

    @classmethod
    async def one_or_none[*Ts](
        cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]
    ) -> sqlalchemy.Row[*Ts] | None:
        return (await cls.session().execute(query)).one_or_none()

    @classmethod
    async def all[*Ts](cls, query: sqlalchemy.Select[*Ts] | sqlalchemy.CompoundSelect[*Ts]) -> list[sqlalchemy.Row[*Ts]]:
        return list((await cls.session().execute(query)).all())

    @classmethod
    async def get_by_id_not_null(
        cls, id_: int, for_update: bool = False, options: sqlalchemy.sql.base.ExecutableOption | None = None
    ) -> typing.Self:
        instance = await cls.get_by_id(id_, for_update=for_update, options=options)
        return _require_instance(instance, cls, id_)

    @classmethod
    async def get_by_id(
        cls, id_: int, for_update: bool = False, options: sqlalchemy.sql.base.ExecutableOption | None = None
    ) -> typing.Self | None:
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
        page_query = _page_query(query, page, per_page)
        total = await cls.count(query)
        items = await (cls.scalars(page_query) if scalar else cls.all(page_query))
        # pylint: disable=protected-access
        return pytilpack.paginator.Paginator(page=page, per_page=per_page, items=items, total=total)

    @classmethod
    def run_with_session[**P, R](cls, func: typing.Callable[P, typing.Awaitable[R]], *args: P.args, **kwargs: P.kwargs) -> R:

        async def wrapper() -> R:
            async with cls.session_scope():
                return await func(*args, **kwargs)

        return pytilpack.asyncio.run(wrapper())


class AsyncUniqueIDMixin(_UniqueIDMixin):
    @classmethod
    async def get_by_unique_id(
        cls: type[typing.Self],
        unique_id: str | int,
        allow_id: bool = False,
        for_update: bool = False,
    ) -> typing.Self | None:
        assert issubclass(cls, AsyncMixin)
        q = cls.select().where(_id_filter(cls, unique_id, not (allow_id and isinstance(unique_id, int))))
        q = _query_options(q, for_update)
        return await cls.scalar_one_or_none(q)


async def await_for_connection(url: str, timeout: float = 180.0) -> None:
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
    try:
        await asyncio.shield(session.close())
    except Exception:
        if log_level is not None:
            logger.log(log_level, "セッションクローズ失敗", exc_info=True)
