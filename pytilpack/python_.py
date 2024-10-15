"""Pythonのユーティリティ集。

本格的にはpydashとか使った方がいいかも…？

"""

import inspect
import re
import typing

T = typing.TypeVar("T")


@typing.overload
def coalesce(iterable: typing.Iterable[T | None], default_value: None = None) -> T:
    pass


@typing.overload
def coalesce(iterable: typing.Iterable[T | None], default_value: T) -> T:
    pass


def coalesce(
    iterable: typing.Iterable[T | None], default_value: T | None = None
) -> T | None:
    """Noneでない最初の要素を取得する。"""
    for item in iterable:
        if item is not None:
            return item
    return default_value


def remove_none(iterable: typing.Iterable[T | None]) -> list[T]:
    """Noneを除去する。"""
    return [item for item in iterable if item is not None]


def find(
    collection: typing.Iterable[T], predicate: typing.Callable[[T], bool]
) -> T | None:
    """条件を満たす最初の要素を取得する。"""
    for item in collection:
        if predicate(item):
            return item
    return None


def find_index(
    collection: typing.Iterable[T], predicate: typing.Callable[[T], bool]
) -> int:
    """条件を満たす最初の要素のインデックスを取得する。"""
    for i, item in enumerate(collection):
        if predicate(item):
            return i
    return -1


def empty(x: typing.Any) -> bool:
    """Noneまたは空の場合にTrueを返す。

    関数名はis_null_or_emptyとかの方が正しいが、
    短く使いたいのでemptyにしている。

    """
    return (
        x is None
        or (isinstance(x, str) and x == "")
        or (hasattr(x, "__len__") and len(x) == 0)
    )


def default(x: typing.Any, default_value: T) -> T:
    """Noneまたは空の場合にデフォルト値を返す。

    関数名はdefault_if_null_or_emptyとかの方が正しいが、
    短く使いたいのでdefaultにしている。

    """
    return default_value if empty(x) else x


def doc_summary(obj: typing.Any) -> str:
    """docstringの先頭1行分を取得する。

    Args:
        obj: ドキュメント文字列を取得する対象。

    Returns:
        docstringの先頭1行分の文字列。取得できなかった場合は""。

    """
    return (
        obj.__doc__.strip().split("\n", 1)[0]
        if hasattr(obj, "__doc__") and not empty(obj.__doc__)
        else ""
    )


def class_field_comments(cls: typing.Any) -> dict[str, str | None]:
    """クラスからクラスフィールド毎のコメントを取得する。"""
    source = inspect.getsource(cls)
    lines = source.splitlines()
    field_comments: dict[str, str | None] = {}
    prev_comment: str | None = None

    comment_pattern = re.compile(r"^\s*#\s*(.*)$")
    field_pattern = re.compile(r"^\s*(\w+)\s*(?:[:=])")

    for line in lines:
        line = line.rstrip()

        # コメント行の場合
        match = comment_pattern.match(line)
        if match:
            if prev_comment is None:
                prev_comment = match.group(1)
            else:
                # 複数行コメントの場合は先頭1行のみ使用する
                pass
            continue

        # クラスフィールド行の場合
        match = field_pattern.match(line)
        if match:
            var_name = match.group(1)
            if (
                var_name not in field_comments  # 上書きしない(先勝ち)
                and prev_comment is not None
            ):
                field_comments[var_name] = prev_comment
                prev_comment = None
        else:
            # コメントでもコードでもない行が出てきたらコメントをリセット
            prev_comment = None

    return field_comments
