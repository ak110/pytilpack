"""SQLAlchemy Mixin共通の基底クラス。"""

__lazy_modules__ = ["datetime", "logging", "secrets", "sqlalchemy", "sqlalchemy.sql.base", "time", "typing"]

import datetime
import logging
import secrets
import time
import typing

import sqlalchemy
import sqlalchemy.sql.base

_SENTINEL = object()

logger = logging.getLogger(__name__)


def _engine_kwargs(
    kwargs: dict[str, typing.Any],
    pool_size: int | None,
    max_overflow: int | None,
    pool_recycle: int | None,
    pool_pre_ping: bool,
    disable_pool: bool = False,
) -> dict[str, typing.Any]:
    """接続オプションを組み立てる。プール無効化の判断は呼出側が行う。"""
    result = kwargs.copy()
    if disable_pool:
        result["poolclass"] = sqlalchemy.pool.NullPool
    else:
        if pool_size is not None:
            result["pool_size"] = pool_size
            if max_overflow is None:
                max_overflow = pool_size
        if max_overflow is not None:
            result["max_overflow"] = max_overflow
    if pool_recycle is not None:
        result["pool_recycle"] = pool_recycle
    if pool_pre_ping is not None:
        result["pool_pre_ping"] = pool_pre_ping
    return result


class _QueryMixin:
    """セッションに依存しないクエリ生成。"""

    @classmethod
    def select(cls) -> sqlalchemy.Select[typing.Self]:
        """FROM句を保持したSELECTを返す。"""
        return sqlalchemy.select(cls).select_from(cls)

    @classmethod
    def insert(cls) -> sqlalchemy.Insert:
        """INSERTを返す。"""
        return sqlalchemy.insert(cls)

    @classmethod
    def update(cls) -> sqlalchemy.Update:
        """UPDATEを返す。"""
        return sqlalchemy.update(cls)

    @classmethod
    def delete(cls) -> sqlalchemy.Delete:
        """DELETEを返す。"""
        return sqlalchemy.delete(cls)


class _UniqueIDMixin:
    """各SQL実装に同じ長さのユニークID生成を提供する。"""

    @classmethod
    def generate_unique_id(cls) -> str:
        """ユニークIDを生成する。"""
        return secrets.token_urlsafe(32)


def _count_query(query: sqlalchemy.Select | sqlalchemy.CompoundSelect) -> sqlalchemy.Select:
    """ソートを除いた副問合せの件数クエリを返す。"""
    return sqlalchemy.select(sqlalchemy.func.count()).select_from(query.order_by(None).subquery())  # pylint: disable=not-callable


def _id_filter(model: type, id_: str | int, unique: bool = False):
    """IDまたはユニークIDの比較条件を返す。"""
    return (model.unique_id if unique else model.id) == id_  # type: ignore[attr-defined]


def _query_options[T](query: T, for_update: bool, options: sqlalchemy.sql.base.ExecutableOption | None = None) -> T:
    """ID検索のオプションと更新ロックを同じ順番で適用する。"""
    configured: typing.Any = query
    if options is not None:
        configured = configured.options(options)
    if for_update:
        configured = configured.with_for_update()
    return typing.cast(T, configured)


def _require_instance[T](instance: T | None, model: type, id_: int) -> T:
    """ID検索が0件の場合のエラーをそろえる。"""
    if instance is None:
        raise ValueError(f"{model.__qualname__}が見つかりませんでした。id={id_}")
    return instance


def _page_query[T: sqlalchemy.Select | sqlalchemy.CompoundSelect](query: T, page: int, per_page: int) -> T:
    """ページ引数を検証し、取得範囲を指定したクエリを返す。"""
    if page <= 0:
        raise ValueError(f"ページ番号は1以上でなければなりません: page={page}")
    if per_page <= 0:
        raise ValueError(f"1ページあたりのアイテム数は1以上でなければなりません: per_page={per_page}")
    return typing.cast(T, query.offset((page - 1) * per_page).limit(per_page))


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
        if includes is not None and excludes is not None:
            raise ValueError("includesとexcludesは同時に指定できません。")
        mapper = sqlalchemy.inspect(self.__class__, raiseerr=True)
        assert mapper is not None  # SQLAlchemyモデルであることがクラス契約で保証される
        all_columns = [
            mapper.get_property_by_column(column).key
            for column in self.__table__.columns  # type: ignore[attr-defined]
        ]
        if includes is None:
            includes = all_columns
            if excludes is not None:
                unknown = set(excludes) - set(all_columns)
                if unknown:
                    raise ValueError(f"excludesに未知のフィールドが含まれています: {sorted(unknown)}")
                includes = list(filter(lambda x: x not in excludes, includes))
        else:
            unknown = set(includes) - set(all_columns)
            if unknown:
                raise ValueError(f"includesに未知のフィールドが含まれています: {sorted(unknown)}")

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
        """接続成功時に呼ぶ。過去に失敗していた場合のみログを出力する。"""
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
