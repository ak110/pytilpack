__lazy_modules__ = ["functools", "inspect", "re", "threading", "typing", "warnings"]

import functools
import inspect
import re
import threading
import typing
import warnings


def deprecated[**P, R](reason: str | None = None) -> typing.Callable[[typing.Callable[P, R]], typing.Callable[P, R]]:

    def decorator(func: typing.Callable[P, R]) -> typing.Callable[P, R]:
        message = f"{func.__name__} is deprecated."
        if reason:
            message += f" {reason}"
        else:
            message += " Stop calling it; see the documentation of the package for a replacement."

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
    for item in iterable:
        if item is not None:
            return item
    return default_value


def remove_none[T](iterable: typing.Iterable[T | None]) -> list[T]:
    return [item for item in iterable if item is not None]


def find[T](collection: typing.Iterable[T], predicate: typing.Callable[[T], bool]) -> T | None:
    for item in collection:
        if predicate(item):
            return item
    return None


def find_index[T](collection: typing.Iterable[T], predicate: typing.Callable[[T], bool]) -> int:
    for i, item in enumerate(collection):
        if predicate(item):
            return i
    return -1


def empty(x: typing.Any) -> bool:
    return x is None or (isinstance(x, str) and x == "") or (hasattr(x, "__len__") and len(x) == 0)


def default[T](x: typing.Any, default_value: T) -> T:
    return default_value if empty(x) else x


def doc_summary(obj: typing.Any) -> str:
    if obj is None:
        return ""
    return obj.__doc__.strip().split("\n", 1)[0] if hasattr(obj, "__doc__") and not empty(obj.__doc__) else ""


def class_field_comments(cls: typing.Any) -> dict[str, str | None]:
    source = inspect.getsource(cls)
    lines = source.splitlines()
    field_comments: dict[str, str | None] = {}
    prev_comment: str | None = None

    comment_pattern = re.compile(r"^\s*#\s*(.*)$")
    field_pattern = re.compile(r"^\s*(\w+)\s*(?:[:=])")

    for line in lines:
        line = line.rstrip()

        match = comment_pattern.match(line)
        if match:
            if prev_comment is None:
                prev_comment = match.group(1)
            continue

        match = field_pattern.match(line)
        if match:
            var_name = match.group(1)
            if var_name not in field_comments and prev_comment is not None:
                field_comments[var_name] = prev_comment
                prev_comment = None
        else:
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
    if default_value is None and expected_type is list:
        default_value = typing.cast(T, [])
    elif default_value is None and expected_type is dict:
        default_value = typing.cast(T, {})
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
    return _get_typed(data, key, bool, default_value, errors, "bool")


def get_int(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: int = 0,
    errors: typing.Literal["strict", "ignore"] = "strict",
) -> int:
    return _get_typed(data, key, int, default_value, errors, "int")


def get_float(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: float = 0.0,
    errors: typing.Literal["strict", "ignore"] = "strict",
) -> float:
    return _get_typed(data, key, float, default_value, errors, "float")


def get_str(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: str = "",
    errors: typing.Literal["strict", "ignore"] = "strict",
) -> str:
    return _get_typed(data, key, str, default_value, errors, "str")


def get_list(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: list | None = None,
    errors: typing.Literal["strict", "ignore"] = "strict",
) -> list:
    return _get_typed(data, key, list, default_value, errors, "list")


def get_dict(
    data: list | dict,
    key: str | int | list[str | int],
    default_value: dict | None = None,
    errors: typing.Literal["strict", "ignore"] = "strict",
) -> dict:
    return _get_typed(data, key, dict, default_value, errors, "dict")


def get[T](
    data: list | dict,
    key: str | int | list[str | int],
    default_value: T | None = None,
    errors: typing.Literal["strict", "ignore"] = "strict",
    default_if_none: bool = True,
) -> T | None:
    if not isinstance(key, list):
        key = [key]
    for k in key:
        if isinstance(data, dict):
            if k in data:
                data = data[k]  # type: ignore[assignment]
            else:
                return default_value
        elif isinstance(data, list):
            if isinstance(k, int):
                if 0 <= k < len(data):
                    data = data[k]  # type: ignore[assignment]
                else:
                    return default_value
            else:
                if errors == "strict":
                    raise ValueError(
                        f"{_stringify_key(key)} not found;"
                        " specify a key that matches the data structure, or pass errors='ignore' to get default_value"
                    )
                return default_value
        else:
            if errors == "strict":
                raise ValueError(
                    f"{_stringify_key(key)} not found;"
                    " specify a key that matches the data structure, or pass errors='ignore' to get default_value"
                )
            return default_value

    if data is None and default_if_none:
        return default_value

    return typing.cast(T, data)


def _stringify_key(key: str | int | list[str | int]) -> str:
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
        constructor = typing.cast(typing.Callable[[typing.Any], T], target_type)
        value = constructor(value)
        return value
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
    if value is None:
        return default_value
    return convert(value, target_type, default_value, errors)


class SingletonMixin:
    _instances: dict[type, typing.Any] = {}

    _lock: threading.RLock = threading.RLock()

    _initializing: set[type] = set()

    def __new__(cls, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        del args, kwargs  # noqa
        raise TypeError(f"{cls.__name__}() は直接インスタンス化できません。{cls.__name__}.get_singleton() を使用してください。")

    @classmethod
    def get_singleton[T](cls: type[T]) -> T:
        with SingletonMixin._lock:
            if cls in SingletonMixin._initializing:
                raise RuntimeError(
                    f"{cls.__name__}の初期化中に同じsingletonが要求されました。初期化の循環参照を解消してください。"
                )
            if cls not in SingletonMixin._instances:
                SingletonMixin._initializing.add(cls)
                try:
                    instance = object.__new__(cls)
                    cls.__init__(instance)  # type: ignore[misc]
                    SingletonMixin._instances[cls] = instance
                finally:
                    SingletonMixin._initializing.remove(cls)
            return typing.cast(T, SingletonMixin._instances[cls])

    @classmethod
    def reset(cls) -> None:
        with SingletonMixin._lock:
            if cls in SingletonMixin._instances:
                del SingletonMixin._instances[cls]


def merge(dst: typing.Any, src: typing.Any) -> typing.Any:
    dst = pydantic_to_dict(dst)
    src = pydantic_to_dict(src)

    if isinstance(dst, dict) and isinstance(src, dict):
        result = dst.copy()
        for key, value in src.items():
            if key in result:
                result[key] = merge(result[key], value)
            else:
                result[key] = value
        return result

    if isinstance(dst, list) and isinstance(src, list):
        return dst + src

    return src


def pydantic_to_dict(obj: typing.Any, **kwargs) -> typing.Any:
    if hasattr(obj, "model_dump") and any("pydantic" in base.__module__ for base in obj.__class__.__mro__):
        obj = obj.model_dump(**({"exclude_unset": True} | kwargs))
    return obj
