"""SQLAlchemy用のユーティリティ集。"""

import logging
import secrets
import time
import typing

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.sql.elements

import pytilpack.python_
import pytilpack.sqlalchemya_

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


class Mixin:
    """テーブルクラスに色々便利機能を生やすMixin。"""

    @classmethod
    def get_by_id(
        cls: type[typing.Self], id_: int, for_update: bool = False
    ) -> typing.Self | None:
        """IDを元にインスタンスを取得。

        Args:
            id_: ID。
            for_update: 更新ロックを取得するか否か。

        Returns:
            インスタンス。

        """
        q = cls.query.filter(cls.id == id_)  # type: ignore
        if for_update:
            q = q.with_for_update()
        return q.one_or_none()

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


class UniqueIDMixin:
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
        if allow_id and isinstance(unique_id, int):
            q = cls.query.filter(cls.id == unique_id)  # type: ignore
        else:
            q = cls.query.filter(cls.unique_id == unique_id)  # type: ignore
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


def describe(
    Base: type[sqlalchemy.orm.DeclarativeBase],
    tablefmt: "str | tabulate.TableFormat" = "grid",
) -> str:
    """DBのテーブル構造を文字列化する。"""
    return "\n".join(
        [
            describe_table(table, get_class_by_table(Base, table), tablefmt=tablefmt)
            for table in Base.metadata.tables.values()
        ]
    )


def get_class_by_table(
    Base: type[sqlalchemy.orm.DeclarativeBase], table: sqlalchemy.schema.Table
) -> type[sqlalchemy.orm.DeclarativeBase]:
    """テーブルからクラスを取得する。"""
    # https://stackoverflow.com/questions/72325242/type-object-base-has-no-attribute-decl-class-registry
    for (
        cls
    ) in Base.registry._class_registry.values():  # pylint: disable=protected-access
        if hasattr(cls, "__table__") and cls.__table__ == table:
            cls = typing.cast(type, cls)
            assert issubclass(cls, sqlalchemy.orm.DeclarativeBase)
            return cls
    raise ValueError(f"テーブル {table.name} に対応するクラスが見つかりませんでした。")


def describe_table(
    table: sqlalchemy.schema.Table,
    orm_class: type[sqlalchemy.orm.DeclarativeBase],
    tablefmt: "str | tabulate.TableFormat" = "grid",
) -> str:
    """テーブル構造を文字列化する。"""
    import tabulate

    try:
        class_field_comments = pytilpack.python_.class_field_comments(orm_class)
    except Exception as e:
        logger.warning(f"クラスフィールドコメント取得失敗: {e}")
        class_field_comments = {}

    headers = ["Field", "Type", "Null", "Key", "Default", "Extra", "Comment"]
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
        elif isinstance(default_value, sqlalchemy.sql.elements.CompilerElement):  # type: ignore[attr-defined]
            default = str(default_value.compile(compile_kwargs={"literal_binds": True}))
        else:
            default = str(default_value)

        # コメントは以下の優先順位で拾う。
        # doc(DBに反映されないもの) > comment(DBに反映されるもの)
        #  > class_field_comments(ソースコード上のコメント)
        comment: str = ""
        if column.doc:
            comment = column.doc
        elif column.comment:
            comment = column.comment
        elif column.name in class_field_comments:
            comment = class_field_comments[column.name] or ""

        rows.append(
            [
                column.name,
                str(column.type),
                "YES" if column.nullable else "NO",
                key,
                default,
                extra,
                comment,
            ]
        )
    table_description = tabulate.tabulate(rows, headers=headers, tablefmt=tablefmt)

    return f"Table: {table.name}\n{table_description}\n"


# エイリアス
AsyncMixin = pytilpack.sqlalchemya_.AsyncMixin
AsyncUniqueIDMixin = pytilpack.sqlalchemya_.AsyncUniqueIDMixin
asafe_close = pytilpack.sqlalchemya_.asafe_close
await_for_connection = pytilpack.sqlalchemya_.await_for_connection
