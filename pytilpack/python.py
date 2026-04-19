"""Pythonのユーティリティ集。

本格的な用途にはpydash等の利用も検討する。

"""

import functools
import inspect
import re
import threading
import typing
import warnings


def deprecated[**P, R](reason: str | None = None) -> typing.Callable[[typing.Callable[P, R]], typing.Callable[P, R]]:
    """DeprecationWarningを発生させるデコレーター。"""

    def decorator(func: typing.Callable[P, R]) -> typing.Callable[P, R]:
        message = f"{func.__name__} is deprecated."
        if reason:
            message += f" {reason}"

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs):
                warnings.warn(message, category=DeprecationWarning, stacklevel=2)
                return await func(*args, **kwargs)

            return typing.cast(typing.Callable[P, R], async_wrapper)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            warnings.warn(message, category=DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return sync_wrapper

    return decorator


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

    関数名はis_null_or_empty等の方が正確であるが、
    短く使いたいためemptyとしている。

    """
    return x is None or (isinstance(x, str) and x == "") or (hasattr(x, "__len__") and len(x) == 0)


def default[T](x: typing.Any, default_value: T) -> T:
    """Noneまたは空の場合にデフォルト値を返す。

    関数名はdefault_if_null_or_empty等の方が正確であるが、
    短く使いたいためdefaultとしている。

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


def _get_typed[T](
    data: list | dict,
    key: str | int | list[str | int],
    expected_type: type[T] | tuple[type[T], ...],
    default_value: T | None,
    errors: typing.Literal["strict", "ignore"],
    type_name: str,
) -> T:
    """辞書またはリストから値を取得し、expected_type型であることを検証する。

    get_bool/get_int/get_float/get_str/get_list/get_dictの共通処理。
    default_valueがNoneの場合は、expected_typeの空インスタンスを採用する
    （list→[]、dict→{}）。
    """
    if default_value is None and expected_type is list:
        default_value = typing.cast(T, [])
    elif default_value is None and expected_type is dict:
        default_value = typing.cast(T, {})
    # int型チェックはboolを誤検知しないよう、get_intでもそのままisinstance(value, int)を使う。
    # （元実装に倣う。boolはintのサブクラスだがget_intはboolもTrueとして受け入れていた）
    value = get(data, key, default_value, errors)
    if isinstance(value, expected_type):
        return value
    if errors == "ignore":
        return typing.cast(T, default_value)
    raise ValueError(f"{_stringify_key(key)} is not {type_name}: {value!r}")


def get_bool(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: bool = False,
    errors: typing.Literal["strict", "ignore"] = "strict",
) -> bool:
    """辞書またはリストからbool値を取得する。"""
    return _get_typed(data, key, bool, default_value, errors, "bool")


def get_int(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: int = 0,
    errors: typing.Literal["strict", "ignore"] = "strict",
) -> int:
    """辞書またはリストからint値を取得する。"""
    return _get_typed(data, key, int, default_value, errors, "int")


def get_float(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: float = 0.0,
    errors: typing.Literal["strict", "ignore"] = "strict",
) -> float:
    """辞書またはリストからfloat値を取得する。"""
    return _get_typed(data, key, float, default_value, errors, "float")


def get_str(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: str = "",
    errors: typing.Literal["strict", "ignore"] = "strict",
) -> str:
    """辞書またはリストからstr値を取得する。"""
    return _get_typed(data, key, str, default_value, errors, "str")


def get_list(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: list | None = None,
    errors: typing.Literal["strict", "ignore"] = "strict",
) -> list:
    """辞書またはリストからlist値を取得する。"""
    return _get_typed(data, key, list, default_value, errors, "list")


def get_dict(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: dict | None = None,
    errors: typing.Literal["strict", "ignore"] = "strict",
) -> dict:
    """辞書またはリストからdict値を取得する。"""
    return _get_typed(data, key, dict, default_value, errors, "dict")


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

    Examples:
        安全な型変換::

            pytilpack.python.convert("123", int, 0)   # => 123
            pytilpack.python.convert("abc", int, 0)   # => 0
            pytilpack.python.convert(None, int, 0)    # => 0

    """
    if value is None:
        return default_value

    if isinstance(value, target_type):
        return value

    if target_type is bool:
        match value:
            case str():
                value = value.lower()
                if value in ("true", "1"):
                    return typing.cast(T, True)
                elif value in ("false", "0"):
                    return typing.cast(T, False)
            case int() if value in (0, 1):
                return typing.cast(T, bool(value))
        if errors == "ignore":
            return default_value
        raise ValueError(f"値の変換に失敗しました: {value!r} to {target_type.__name__}")

    try:
        # intなどを想定した型変換
        value = target_type(value)  # type: ignore[call-arg]
        return typing.cast(T, value)
    except Exception as e:
        if errors == "ignore":
            return default_value
        raise ValueError(f"値の変換に失敗しました: {value!r} to {target_type.__name__}") from e


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

    dictは再帰的にマージし、listは結合し、それ以外はsrcで上書きする。

    Args:
        dst: マージ先のオブジェクト。
        src: マージ元のオブジェクト。

    Returns:
        マージされたオブジェクト。

    Examples:
        辞書の再帰的マージ::

            pytilpack.python.merge(
                {"a": {"x": 1}, "b": [1, 2]},
                {"a": {"y": 2}, "b": [3]},
            )
            # => {"a": {"x": 1, "y": 2}, "b": [1, 2, 3]}

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
