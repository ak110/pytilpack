"""SQLAlchemy用のユーティリティ集（Flask-SQLAlchemy版）。"""

import logging
import secrets
import typing

import sqlalchemy
import sqlalchemy.event
import sqlalchemy.exc
import sqlalchemy.pool
import sqlalchemy.sql.base

from pytilpack.sqlalchemy._base import _ReprMixin, _ToDictMixin

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


class Mixin(_ReprMixin, _ToDictMixin):
    """テーブルクラスに色々便利機能を生やすMixin。"""

    @classmethod
    def get_by_id_not_null(
        cls, id_: int, for_update: bool = False, options: sqlalchemy.sql.base.ExecutableOption | None = None
    ) -> typing.Self:
        """IDを元にインスタンスを取得。見つからない場合は例外を出す。

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
        if instance is None:
            raise ValueError(f"{cls.__qualname__}が見つかりませんでした。id={id_}")
        return instance

    @classmethod
    def get_by_id(
        cls: type[typing.Self], id_: int, for_update: bool = False, options: sqlalchemy.sql.base.ExecutableOption | None = None
    ) -> typing.Self | None:
        """IDを元にインスタンスを取得。

        Args:
            id_: ID。
            for_update: 更新ロックを取得するか否か。
            options: クエリオプション。eager loadingなどに使用。

        Returns:
            インスタンス。

        """
        q = cls.query.filter(cls.id == id_)  # type: ignore
        if options is not None:
            q = q.options(options)
        if for_update:
            q = q.with_for_update()
        return q.one_or_none()


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
