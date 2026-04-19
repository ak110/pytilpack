"""SQLAlchemy Mixin共通の基底クラス。"""

import datetime
import logging
import time
import typing

import sqlalchemy

_SENTINEL = object()

logger = logging.getLogger(__name__)


class _ReprMixin:
    """__repr__を提供する共通Mixin。"""

    def _repr_attrs(self) -> dict[str, typing.Any]:
        """__repr__で表示する属性を返す。派生クラスでオーバーライド可能。"""
        id_ = getattr(self, "id", _SENTINEL)
        if id_ is not _SENTINEL:
            return {"id": id_}
        return {}

    def __repr__(self) -> str:
        # detached/expired状態でのDetachedInstanceErrorなどを防ぐ
        try:
            attrs = self._repr_attrs()
            attrs_str = ", ".join(f"{k}={v!r}" for k, v in attrs.items())
            return f"<{self.__class__.__module__}.{self.__class__.__qualname__}({attrs_str})>"
        except Exception:
            return f"<{self.__class__.__module__}.{self.__class__.__qualname__}>"


class _ToDictMixin:
    """to_dict()メソッドを提供する共通Mixin。sync/async/flask版Mixinで共用する。"""

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


class _WaitForConnectionState:
    """wait_for_connection/await_for_connectionで共有する状態管理。

    sync/asyncで接続取得方法・sleep関数が異なるため、ループそのものは各呼び出し側に
    残す。共通化は開始時刻の保持・初回失敗時のログ出力・タイムアウト判定に留める。
    """

    def __init__(self, url: str, timeout: float) -> None:
        self.url = url
        self.timeout = timeout
        self.start_time = time.time()
        self.failed = False

    def on_success(self) -> None:
        """接続成功時に呼ぶ。過去に失敗していた場合のみログを出す。"""
        if self.failed:
            logger.info("DB接続成功")

    def on_failure(self, exc: BaseException) -> float:
        """接続失敗時に呼ぶ。残り時間を返す。0以下ならRuntimeErrorを送出する。"""
        if not self.failed:
            self.failed = True
            logger.info(f"DB接続待機中 . . . (URL: {self.url})")
        remain_time = self.timeout - (time.time() - self.start_time)
        if remain_time <= 0:
            raise RuntimeError(f"DB接続タイムアウト (URL: {self.url})") from exc
        return min(1, remain_time)
