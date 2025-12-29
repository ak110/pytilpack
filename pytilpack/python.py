"""Pythonのユーティリティ集。

本格的にはpydashとか使った方がいいかも…？

"""

import inspect
import re
import threading
import typing


@typing.overload
def coalesce[T](iterable: typing.Iterable[T | None], default_value: None = None) -> T:
    pass


@typing.overload
def coalesce[T](iterable: typing.Iterable[T | None], default_value: T) -> T:
    pass


def coalesce[T](iterable: typing.Iterable[T | None], default_value: T | None = None) -> T | None:
    """Noneでない最初の要素を取得する。"""
    for item in iterable:
        if item is not None:
            return item
    return default_value


def remove_none[T](iterable: typing.Iterable[T | None]) -> list[T]:
    """Noneを除去する。"""
    return [item for item in iterable if item is not None]


def find[T](collection: typing.Iterable[T], predicate: typing.Callable[[T], bool]) -> T | None:
    """条件を満たす最初の要素を取得する。"""
    for item in collection:
        if predicate(item):
            return item
    return None


def find_index[T](collection: typing.Iterable[T], predicate: typing.Callable[[T], bool]) -> int:
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
    return x is None or (isinstance(x, str) and x == "") or (hasattr(x, "__len__") and len(x) == 0)


def default[T](x: typing.Any, default_value: T) -> T:
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
    return obj.__doc__.strip().split("\n", 1)[0] if hasattr(obj, "__doc__") and not empty(obj.__doc__) else ""


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


def get[T](
    data: list | dict,
    key: str | int | list[str | int],
    default_value: T | None = None,
    errors: typing.Literal["strict", "ignore"] = "strict",
    default_if_none: bool = True,
) -> T | None:
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

    return typing.cast(T, data)


def _stringify_key(key: str | int | list[str | int]) -> str:
    """キーを文字列化。"""
    if isinstance(key, list):
        return "".join(_stringify_key(k) for k in key)
    if isinstance(key, int):
        return f"[{key}]"
    return f".{key}"


def convert[T](
    value: typing.Any,
    target_type: type[T],
    default_value: T,
    errors: typing.Literal["strict", "ignore"] = "ignore",
) -> T:
    """値をTの型に変換する。

    Args:
        value: 変換元の値。
        target_type: 変換先の型。
        default_value: 取得できなかった場合のデフォルト値。
        errors: エラー時の挙動。"strict"で例外を発生させる。"ignore"でデフォルト値を返す。

    Returns:
        取得した値。取得できなかった場合はdefault_value。

    Raises:
        ValueError: errors="strict"の場合で値の変換に失敗した場合に発生。

    """
    if value is None:
        return default_value

    if isinstance(value, target_type):
        return value

    if target_type is bool:
        if isinstance(value, str):
            value = value.lower()
            if value in ("true", "1"):
                return typing.cast(T, True)
            elif value in ("false", "0"):
                return typing.cast(T, False)
            else:
                if errors == "ignore":
                    return default_value
                raise ValueError(f"値の変換失敗: {value!r} to {target_type.__name__}")
        elif isinstance(value, int) and value in (0, 1):
            return typing.cast(T, bool(value))
        else:
            if errors == "ignore":
                return default_value
            raise ValueError(f"値の変換失敗: {value!r} to {target_type.__name__}")

    try:
        # intなどを想定した型変換
        value = target_type(value)  # type: ignore[call-arg]
        return typing.cast(T, value)
    except Exception as e:
        if errors == "ignore":
            return default_value
        raise ValueError(f"値の変換失敗: {value!r} to {target_type.__name__}") from e


def convert_or_none[T](
    value: typing.Any,
    target_type: type[T],
    default_value: T | None = None,
    errors: typing.Literal["strict", "ignore"] = "ignore",
) -> T | None:
    """値をTの型に変換する。Noneの場合はデフォルト値を返す。

    Args:
        value: 変換元の値。
        target_type: 変換先の型。
        default_value: 取得できなかった場合のデフォルト値。
        errors: エラー時の挙動。"strict"で例外を発生させる。"ignore"でデフォルト値を返す。

    Returns:
        取得した値。取得できなかった場合はdefault_value。

    Raises:
        ValueError: errors="strict"の場合で値の変換に失敗した場合に発生。

    """
    if value is None:
        return default_value
    return convert(value, target_type, default_value, errors)


class SingletonMixin:
    """シングルトンパターンを提供するMixin。

    Examples:
        使用例::

            class MyConfig(SingletonMixin):
                def __init__(self):
                    self.value = "test"

            config1 = MyConfig.get_singleton()
            config2 = MyConfig.get_singleton()
            assert config1 is config2  # 同じインスタンス

            MyConfig.reset()
            config3 = MyConfig.get_singleton()
            assert config1 is not config3  # 新しいインスタンス

    """

    _instances: dict[type, typing.Any] = {}
    """シングルトンインスタンスを保持する辞書。"""

    _lock: threading.Lock = threading.Lock()
    """スレッドセーフ用のロック。"""

    _initialized: dict[type, bool] = {}
    """初期化済みフラグ。"""

    def __new__(cls, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        """直接インスタンス化を禁止する。"""
        del args, kwargs  # noqa
        raise TypeError(f"{cls.__name__}() は直接インスタンス化できません。{cls.__name__}.get_singleton() を使用してください。")

    @classmethod
    def get_singleton[T](cls: type[T]) -> T:
        """シングルトンインスタンスを取得する。"""
        # ダブルチェックロッキングパターン
        if cls not in SingletonMixin._instances:
            with SingletonMixin._lock:
                if cls not in SingletonMixin._instances:
                    # object.__new__() を使ってインスタンスを作成
                    instance = object.__new__(cls)
                    SingletonMixin._instances[cls] = instance
                    # __init__() を初回のみ実行
                    if cls not in SingletonMixin._initialized:
                        cls.__init__(instance)  # type: ignore[misc]
                        SingletonMixin._initialized[cls] = True
        return typing.cast(T, SingletonMixin._instances[cls])

    @classmethod
    def reset(cls) -> None:
        """シングルトンインスタンスをクリアする。"""
        with SingletonMixin._lock:
            if cls in SingletonMixin._instances:
                del SingletonMixin._instances[cls]
            if cls in SingletonMixin._initialized:
                del SingletonMixin._initialized[cls]


def merge(dst: typing.Any, src: typing.Any) -> typing.Any:
    """2つのオブジェクトをマージする。

    Args:
        dst: マージ先のオブジェクト。
        src: マージ元のオブジェクト。

    Returns:
        マージされたオブジェクト。

    """
    # pydanticモデルの場合はdictに変換
    dst = pydantic_to_dict(dst)
    src = pydantic_to_dict(src)

    # 両方がdictの場合は再帰的にマージ
    if isinstance(dst, dict) and isinstance(src, dict):
        result = dst.copy()
        for key, value in src.items():
            if key in result:
                result[key] = merge(result[key], value)
            else:
                result[key] = value
        return result

    # 両方がリストの場合は結合
    if isinstance(dst, list) and isinstance(src, list):
        return dst + src

    # それ以外の場合はsrcで上書き
    return src


def pydantic_to_dict(obj: typing.Any, **kwargs) -> typing.Any:
    """pydanticモデルの場合はmodel_dumpでdictに変換する。"""
    if hasattr(obj, "model_dump") and any("pydantic" in base.__module__ for base in obj.__class__.__mro__):
        obj = obj.model_dump(**({"exclude_unset": True} | kwargs))
    return obj
