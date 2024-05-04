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
