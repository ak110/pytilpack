"""Pythonのユーティリティ集。"""

import typing

T = typing.TypeVar("T")


@typing.overload
def coalesce(iterable: typing.Iterable[T | None], default: None = None) -> T:
    pass


@typing.overload
def coalesce(iterable: typing.Iterable[T | None], default: T) -> T:
    pass


def coalesce(iterable: typing.Iterable[T | None], default: T | None = None) -> T | None:
    """Noneでない最初の要素を取得する。"""
    for item in iterable:
        if item is not None:
            return item
    return default


def remove_none(iterable: typing.Iterable[T | None]) -> list[T]:
    """Noneを除去する。"""
    return [item for item in iterable if item is not None]


def is_null_or_empty(x: typing.Any) -> bool:
    """Noneまたは空の場合にTrueを返す。"""
    return (
        x is None
        or (isinstance(x, str) and x == "")
        or (hasattr(x, "__len__") and len(x) == 0)
    )


def default_if_null_or_empty(x: typing.Any, default: T) -> T:
    """Noneまたは空の場合にデフォルト値を返す。"""
    return default if is_null_or_empty(x) else x
