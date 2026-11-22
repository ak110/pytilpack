__lazy_modules__ = ["datetime", "logging", "secrets", "sqlalchemy", "sqlalchemy.sql.base", "time", "typing"]

import datetime as dt
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
    @classmethod
    def select(cls) -> sqlalchemy.Select[typing.Self]:
        return sqlalchemy.select(cls).select_from(cls)

    @classmethod
    def insert(cls) -> sqlalchemy.Insert:
        return sqlalchemy.insert(cls)

    @classmethod
    def update(cls) -> sqlalchemy.Update:
        return sqlalchemy.update(cls)

    @classmethod
    def delete(cls) -> sqlalchemy.Delete:
        return sqlalchemy.delete(cls)


class _UniqueIDMixin:
    @classmethod
    def generate_unique_id(cls) -> str:
        return secrets.token_urlsafe(32)


def _count_query(query: sqlalchemy.Select | sqlalchemy.CompoundSelect) -> sqlalchemy.Select:
    return sqlalchemy.select(sqlalchemy.func.count()).select_from(query.order_by(None).subquery())  # pylint: disable=not-callable


def _id_filter(model: type, id_: str | int, unique: bool = False):
    return (model.unique_id if unique else model.id) == id_  # type: ignore[attr-defined]


def _query_options[T](query: T, for_update: bool, options: sqlalchemy.sql.base.ExecutableOption | None = None) -> T:
    configured: typing.Any = query
    if options is not None:
        configured = configured.options(options)
    if for_update:
        configured = configured.with_for_update()
    return typing.cast(T, configured)


def _require_instance[T](instance: T | None, model: type, id_: int) -> T:
    if instance is None:
        raise ValueError(
            f"{model.__qualname__}が見つかりませんでした。id={id_}。"
            "存在するIDを指定するか、見つからない場合にNoneを返すget_by_id()を使う"
        )
    return instance


def _page_query[T: sqlalchemy.Select | sqlalchemy.CompoundSelect](query: T, page: int, per_page: int) -> T:
    if page <= 0:
        raise ValueError(f"ページ番号は1以上でなければなりません: page={page}")
    if per_page <= 0:
        raise ValueError(f"1ページあたりのアイテム数は1以上でなければなりません: per_page={per_page}")
    return typing.cast(T, query.offset((page - 1) * per_page).limit(per_page))


class _ReprMixin:
    def _repr_attrs(self) -> dict[str, typing.Any]:
        id_ = getattr(self, "id", _SENTINEL)
        if id_ is not _SENTINEL:
            return {"id": id_}
        return {}

    def __repr__(self) -> str:
        try:
            attrs = self._repr_attrs()
            attrs_str = ", ".join(f"{k}={v!r}" for k, v in attrs.items())
            return f"<{self.__class__.__module__}.{self.__class__.__qualname__}({attrs_str})>"
        except Exception:
            return f"<{self.__class__.__module__}.{self.__class__.__qualname__}>"


class _ToDictMixin:
    def to_dict(
        self,
        includes: list[str] | None = None,
        excludes: list[str] | None = None,
        exclude_none: bool = False,
        value_converter: typing.Callable[[typing.Any], typing.Any] | None = None,
        datetime_to_iso: bool = True,
    ) -> dict[str, typing.Any]:
        if includes is not None and excludes is not None:
            raise ValueError("includesとexcludesは同時に指定できません。")
        mapper = sqlalchemy.inspect(self.__class__, raiseerr=True)
        assert mapper is not None
        all_columns = [
            mapper.get_property_by_column(column).key
            for column in self.__table__.columns  # type: ignore[attr-defined]
        ]
        if includes is None:
            includes = all_columns
            if excludes is not None:
                unknown = set(excludes) - set(all_columns)
                if unknown:
                    raise ValueError(
                        f"excludesに未知のフィールドが含まれています: {sorted(unknown)}。指定できるフィールド: {all_columns}"
                    )
                includes = list(filter(lambda x: x not in excludes, includes))
        else:
            unknown = set(includes) - set(all_columns)
            if unknown:
                raise ValueError(
                    f"includesに未知のフィールドが含まれています: {sorted(unknown)}。指定できるフィールド: {all_columns}"
                )

        def convert_value(value: typing.Any) -> typing.Any:
            if datetime_to_iso and isinstance(value, dt.datetime | dt.date):
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
    def __init__(self, url: str, timeout: float) -> None:
        self.url = url
        self.timeout = timeout
        self.start_time = time.time()
        self.failed = False

    def on_success(self) -> None:
        if self.failed:
            logger.info("DB接続成功")

    def on_failure(self, exc: BaseException) -> float:
        if not self.failed:
            self.failed = True
            logger.info(f"DB接続待機中 . . . (URL: {self.url})")
        remain_time = self.timeout - (time.time() - self.start_time)
        if remain_time <= 0:
            raise RuntimeError(
                f"DB接続タイムアウト (URL: {self.url}、待機: {self.timeout}秒)。"
                "DBサーバーが起動して接続を受け付けるかを確かめるか、timeout（CLIでは--timeout）を延ばして再実行する"
            ) from exc
        return min(1, remain_time)
