"""SQLAlchemy用のユーティリティ集（Flask-SQLAlchemy版）。"""

import logging
import secrets
import typing

import sqlalchemy
import sqlalchemy.event
import sqlalchemy.exc
import sqlalchemy.pool

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
