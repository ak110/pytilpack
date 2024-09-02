"""SQLAlchemy用のユーティリティ集。"""

import logging
import time
import typing

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.sql.elements

try:
    from typing import Self  # type: ignore[attr-defined]
except ImportError:
    from typing_extensions import Self

if typing.TYPE_CHECKING:
    import tabulate

logger = logging.getLogger(__name__)


def register_ping():
    """コネクションプールの切断対策。"""

    @sqlalchemy.event.listens_for(sqlalchemy.pool.Pool, "checkout")
    def _ping_connection(dbapi_connection, connection_record, connection_proxy):
        """コネクションプールの切断対策。"""
        _ = connection_record, connection_proxy  # noqa
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SELECT 1")
        except Exception as e:
            raise sqlalchemy.exc.DisconnectionError() from e
        finally:
            cursor.close()


class IDMixin:
    """models.Class.query.get()がdeprecatedになるため"""

    @classmethod
    def get_by_id(cls: type[Self], id_: int, for_update: bool = False) -> Self | None:
        """IDを元にインスタンスを取得。"""
        q = cls.query.filter(cls.id == id_)  # type: ignore
        if for_update:
            q = q.with_for_update()
        return q.one_or_none()


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
                try:
                    # 接続成功
                    if failed:
                        logger.info("DB接続成功")
                    break
                finally:
                    result.close()
            finally:
                engine.dispose()
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


def describe(
    metadata: sqlalchemy.MetaData, tablefmt: "str | tabulate.TableFormat" = "grid"
) -> str:
    """DBのテーブル構造を文字列化する。"""
    return "\n".join(
        [describe_table(table, tablefmt=tablefmt) for table in metadata.sorted_tables]
    )


def describe_table(
    table: sqlalchemy.schema.Table, tablefmt: "str | tabulate.TableFormat" = "grid"
) -> str:
    """テーブル構造を文字列化する。"""
    import tabulate

    headers = ["Field", "Type", "Null", "Key", "Default", "Extra"]
    rows = []
    for column in table.columns:
        key = ""
        if column.primary_key:
            key = "PRI"
        elif column.unique:
            key = "UNI"
        elif column.index:
            key = "MUL"

        extra = ""
        if column.autoincrement and column.primary_key:
            extra = "auto_increment"

        default_value = (
            column.default.arg
            if column.default is not None and hasattr(column.default, "arg")
            else column.default
        )
        default: str
        if default_value is None:
            default = "NULL"
        elif callable(default_value):
            default = "(function)"
        elif isinstance(default_value, sqlalchemy.sql.elements.CompilerElement):
            default = str(default_value.compile(compile_kwargs={"literal_binds": True}))
        else:
            default = str(default_value)

        rows.append(
            [
                column.name,
                str(column.type),
                "YES" if column.nullable else "NO",
                key,
                default,
                extra,
            ]
        )
    table_description = tabulate.tabulate(rows, headers=headers, tablefmt=tablefmt)

    return f"Table: {table.name}\n{table_description}\n"
