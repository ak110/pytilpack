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
    if obj is None:
        return ""
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


def get_bool(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: bool = False,
    errors: typing.Literal["strict", "ignore"] = "strict",
) -> bool:
    """辞書またはリストからbool値を取得する。"""
    value = get(data, key, default_value, errors)
    if isinstance(value, bool):
        return value
    if errors == "ignore":
        return default_value
    raise ValueError(f"{_stringify_key(key)} is not bool: {value!r}")


def get_int(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: int = 0,
    errors: typing.Literal["strict", "ignore"] = "strict",
) -> int:
    """辞書またはリストからint値を取得する。"""
    value = get(data, key, default_value, errors)
    if isinstance(value, int):
        return value
    if errors == "ignore":
        return default_value
    raise ValueError(f"{_stringify_key(key)} is not int: {value!r}")


def get_float(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: float = 0.0,
    errors: typing.Literal["strict", "ignore"] = "strict",
) -> float:
    """辞書またはリストからfloat値を取得する。"""
    value = get(data, key, default_value, errors)
    if isinstance(value, float):
        return value
    if errors == "ignore":
        return default_value
    raise ValueError(f"{_stringify_key(key)} is not float: {value!r}")


def get_str(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: str = "",
    errors: typing.Literal["strict", "ignore"] = "strict",
) -> str:
    """辞書またはリストからstr値を取得する。"""
    value = get(data, key, default_value, errors)
    if isinstance(value, str):
        return value
    if errors == "ignore":
        return default_value
    raise ValueError(f"{_stringify_key(key)} is not str: {value!r}")


def get_list(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: list | None = None,
    errors: typing.Literal["strict", "ignore"] = "strict",
) -> list:
    """辞書またはリストからlist値を取得する。"""
    if default_value is None:
        default_value = []
    value = get(data, key, default_value, errors)
    if isinstance(value, list):
        return value
    if errors == "ignore":
        return default_value
    raise ValueError(f"{_stringify_key(key)} is not list: {value!r}")


def get_dict(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: dict | None = None,
    errors: typing.Literal["strict", "ignore"] = "strict",
) -> dict:
    """辞書またはリストからdict値を取得する。"""
    if default_value is None:
        default_value = {}
    value = get(data, key, default_value, errors)
    if isinstance(value, dict):
        return value
    if errors == "ignore":
        return default_value
    raise ValueError(f"{_stringify_key(key)} is not dict: {value!r}")


def get(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: T | None = None,
    errors: typing.Literal["strict", "ignore"] = "strict",
    default_if_none: bool = True,
) -> typing.Any | None:
    """辞書またはリストから値を取得する。

    Args:
        data: 取得元の辞書またはリスト。
        key: 取得する値のキー。
        default_value: 取得できなかった場合のデフォルト値。
        errors: エラー時の挙動。"strict"で例外を発生させる。"ignore"でデフォルト値を返す。
        default_if_none: 値がNoneの場合にデフォルト値を返すか否か。

    Returns:
        取得した値。取得できなかった場合はdefault_value。

    Raises:
        ValueError: errors="strict"の場合、キー/インデックスが見つからない場合やNoneの場合に発生。

    """
    if not isinstance(key, list):
        key = [key]
    for k in key:
        if isinstance(data, dict):
            if k in data:
                data = data[k]  # type: ignore[assignment]
            else:
                return default_value  # key not found
        elif isinstance(data, list):
            if isinstance(k, int):
                if 0 <= k < len(data):
                    data = data[k]  # type: ignore[assignment]
                else:
                    return default_value  # key not found
            else:
                # key error
                if errors == "strict":
                    raise ValueError(f"{_stringify_key(key)} not found")
                return default_value
        else:
            # data error
            if errors == "strict":
                raise ValueError(f"{_stringify_key(key)} not found")
            return default_value

    # 値がNoneの場合
    if data is None and default_if_none:
        return default_value

    return data


def _stringify_key(key: str | int | list[str | int]) -> str:
    """キーを文字列化。"""
    if isinstance(key, list):
        return "".join(_stringify_key(k) for k in key)
    if isinstance(key, int):
        return f"[{key}]"
    return f".{key}"
