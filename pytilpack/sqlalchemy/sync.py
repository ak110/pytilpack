"""SQLAlchemy用のユーティリティ集（同期版）。"""

import asyncio
import atexit
import contextlib
import contextvars
import datetime
import functools
import logging
import secrets
import threading
import time
import typing

import sqlalchemy
import sqlalchemy.engine
import sqlalchemy.orm

import pytilpack.asyncio
import pytilpack.paginator

logger = logging.getLogger(__name__)


class SyncMixin:
    """モデルのベースクラス。SQLAlchemy 2.0スタイル・同期前提。

    Examples:
        モデル定義例::

            class Base(sqlalchemy.orm.DeclarativeBase, pytilpack.sqlalchemy_.sync_.SyncMixin):
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
            **kwargs: sqlalchemy.create_engineに渡す追加のキーワード引数。

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

        cls.engine = sqlalchemy.create_engine(url, **kwargs)
        atexit.register(cls.engine.dispose)

        cls.sessionmaker = sqlalchemy.orm.sessionmaker(cls.engine, autoflush=autoflush, expire_on_commit=expire_on_commit)

    @classmethod
    def connect(cls) -> sqlalchemy.Connection:
        """DBに接続する。

        使用例::
            with Base.connect() as conn:
                Base.metadata.create_all(conn)

        """
        assert cls.engine is not None
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
        assert cls.sessionmaker is not None
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
        assert cls.sessionmaker is not None
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
        assert cls.sessionmaker is not None
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

    @classmethod
    def close_session(
        cls, token: contextvars.Token[sqlalchemy.orm.Session], name: str | None = None, log_level: int = logging.DEBUG
    ) -> None:
        """セッションを終了する。"""
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

    @classmethod
    def session(cls) -> sqlalchemy.orm.Session:
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
    def count(cls, query: sqlalchemy.Select | sqlalchemy.CompoundSelect) -> int:
        """queryのレコード数を取得する。"""
        # pylint: disable=not-callable
        return (
            cls.scalar_one_or_none(sqlalchemy.select(sqlalchemy.func.count()).select_from(query.order_by(None).subquery())) or 0
        )

    @classmethod
    def scalar_one[T](cls, query: sqlalchemy.Select[tuple[T]] | sqlalchemy.CompoundSelect[tuple[T]]) -> T:
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
    def scalar_one_or_none[T](cls, query: sqlalchemy.Select[tuple[T]] | sqlalchemy.CompoundSelect[tuple[T]]) -> T | None:
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
    def scalars[T](cls, query: sqlalchemy.Select[tuple[T]] | sqlalchemy.CompoundSelect[tuple[T]]) -> list[T]:
        """queryの結果を全件取得する。

        Args:
            query: クエリ。

        Returns:
            全件のインスタンスのリスト。

        """
        return list(cls.session().execute(query).scalars().all())

    @classmethod
    def one[TT: tuple](cls, query: sqlalchemy.Select[TT] | sqlalchemy.CompoundSelect[TT]) -> sqlalchemy.Row[TT]:
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
    def one_or_none[TT: tuple](cls, query: sqlalchemy.Select[TT] | sqlalchemy.CompoundSelect[TT]) -> sqlalchemy.Row[TT] | None:
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
    def all[TT: tuple](cls, query: sqlalchemy.Select[TT] | sqlalchemy.CompoundSelect[TT]) -> list[sqlalchemy.Row[TT]]:
        """queryの結果を全件取得する。

        Args:
            query: クエリ。

        Returns:
            全件のインスタンスのリスト。

        """
        return list(cls.session().execute(query).all())

    @classmethod
    def get_by_id(cls, id_: int, for_update: bool = False) -> typing.Self | None:
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
        assert page > 0, "ページ番号は1以上でなければなりません。"
        assert per_page > 0, "1ページあたりのアイテム数は1以上でなければなりません。"
        total = cls.count(query)
        page_query = query.offset((page - 1) * per_page).limit(per_page)
        items = cls.scalars(page_query) if scalar else cls.all(page_query)
        # pylint: disable=protected-access
        return pytilpack.paginator.Paginator(page=page, per_page=per_page, items=items, total=total)

    @classmethod
    def commit(cls) -> None:
        """セッションをコミットする。"""
        cls.session().commit()

    # 非同期版
    # 注意: これらのメソッドは別スレッドで独立したセッション・トランザクションを使用します。

    @classmethod
    async def acount(cls, query: sqlalchemy.Select | sqlalchemy.CompoundSelect) -> int:
        """queryのレコード数を取得する。(非同期版)"""
        return await run_sync_with_session(cls.count.__func__)(cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def ascalar_one[T](cls, query: sqlalchemy.Select[tuple[T]] | sqlalchemy.CompoundSelect[tuple[T]]) -> T:
        """queryの結果を1件取得する。(非同期版)"""
        return await run_sync_with_session(cls.scalar_one.__func__)(cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def ascalar_one_or_none[T](cls, query: sqlalchemy.Select[tuple[T]] | sqlalchemy.CompoundSelect[tuple[T]]) -> T | None:
        """queryの結果を0件または1件取得する。(非同期版)"""
        return await run_sync_with_session(cls.scalar_one_or_none.__func__)(cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def ascalars[T](cls, query: sqlalchemy.Select[tuple[T]] | sqlalchemy.CompoundSelect[tuple[T]]) -> list[T]:
        """queryの結果を全件取得する。(非同期版)"""
        return await run_sync_with_session(cls.scalars.__func__)(cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def aone[TT: tuple](cls, query: sqlalchemy.Select[TT] | sqlalchemy.CompoundSelect[TT]) -> sqlalchemy.Row[TT]:
        """queryの結果を1件取得する。(非同期版)"""
        return await run_sync_with_session(cls.one.__func__)(cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def aone_or_none[TT: tuple](
        cls, query: sqlalchemy.Select[TT] | sqlalchemy.CompoundSelect[TT]
    ) -> sqlalchemy.Row[TT] | None:
        """queryの結果を0件または1件取得する。(非同期版)"""
        return await run_sync_with_session(cls.one_or_none.__func__)(cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def aall[TT: tuple](cls, query: sqlalchemy.Select[TT] | sqlalchemy.CompoundSelect[TT]) -> list[sqlalchemy.Row[TT]]:
        """queryの結果を全件取得する。(非同期版)"""
        return await run_sync_with_session(cls.all.__func__)(cls, query)  # type: ignore[attr-defined]

    @classmethod
    async def aget_by_id(cls, id_: int, for_update: bool = False) -> typing.Self | None:
        """IDを元にインスタンスを取得。(非同期版)"""
        return await run_sync_with_session(cls.get_by_id.__func__)(cls, id_, for_update)  # type: ignore[attr-defined]

    @classmethod
    async def apaginate(
        cls,
        query: sqlalchemy.Select | sqlalchemy.CompoundSelect,
        page: int,
        per_page: int,
        scalar: bool = True,
    ) -> pytilpack.paginator.Paginator:
        """Flask-SQLAlchemy風ページネーション。(非同期版)"""
        return await run_sync_with_session(cls.paginate.__func__)(cls, query, page, per_page, scalar)  # type: ignore[attr-defined]

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


class SyncUniqueIDMixin:
    """self.unique_idを持つテーブルクラスに便利メソッドを生やすmixin。"""

    @classmethod
    def generate_unique_id(cls) -> str:
        """ユニークIDを生成する。"""
        return secrets.token_urlsafe(32)

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
        if allow_id and isinstance(unique_id, int):
            q = cls.select().where(cls.id == unique_id)  # type: ignore
        else:
            q = cls.select().where(cls.unique_id == unique_id)  # type: ignore
        if for_update:
            q = q.with_for_update()
        return cls.scalar_one_or_none(q)


def wait_for_connection(url: str, timeout: float = 60.0) -> None:
    """DBに接続可能になるまで待機する。"""
    failed = False
    start_time = time.time()
    while True:
        try:
            engine = sqlalchemy.create_engine(url)
            try:
                with engine.connect() as connection:
                    result = connection.execute(sqlalchemy.text("SELECT 1"))
                    result.close()
            finally:
                engine.dispose()
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
            time.sleep(1)


def safe_close(
    session: sqlalchemy.orm.Session | sqlalchemy.orm.scoped_session,
    log_level: int | None = logging.DEBUG,
):
    """例外を出さずにセッションをクローズ。"""
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
