"""SQLAlchemy用のユーティリティ集。"""

import logging
import typing

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.sql.elements
import sqlalchemy.sql.schema

import pytilpack.python

if typing.TYPE_CHECKING:
    import tabulate

logger = logging.getLogger(__name__)


def describe(
    Base: type[sqlalchemy.orm.DeclarativeBase],
    tablefmt: "str | tabulate.TableFormat" = "grid",
) -> str:
    """DBのテーブル構造を文字列化する。"""
    return "\n".join(
        [describe_table(table, get_class_by_table(Base, table), tablefmt=tablefmt) for table in Base.metadata.tables.values()]
    )


def get_class_by_table(
    base: type[sqlalchemy.orm.DeclarativeBase], table: sqlalchemy.sql.schema.Table
) -> type[sqlalchemy.orm.DeclarativeBase]:
    """テーブルからクラスを取得する。"""
    for mapper in base.registry.mappers:
        if mapper.local_table is table:
            return typing.cast(type[sqlalchemy.orm.DeclarativeBase], mapper.class_)
    raise ValueError(f"テーブル {table.name} に対応するクラスが見つかりませんでした。")


def describe_table(
    table: sqlalchemy.sql.schema.Table,
    orm_class: type[sqlalchemy.orm.DeclarativeBase],
    tablefmt: "str | tabulate.TableFormat" = "grid",
) -> str:
    """テーブル構造を文字列化する。"""
    import tabulate

    try:
        class_field_comments = pytilpack.python.class_field_comments(orm_class)
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
            if column.default is not None and isinstance(column.default, sqlalchemy.sql.schema.ColumnDefault)
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
