__lazy_modules__ = ["dataclasses", "types", "typing"]

import dataclasses
import types
import typing


def get_literal_values(literal_type: typing.Any) -> list:
    if isinstance(literal_type, typing.TypeAliasType):
        return get_literal_values(literal_type.__value__)

    args = list(typing.get_args(literal_type))
    if len(args) == 0:
        return [literal_type]
    return [sub_arg for arg in args for sub_arg in get_literal_values(arg)]


def is_instance_safe(value: typing.Any, expected_type: typing.Any, path: str = "") -> bool:
    try:
        return is_instance(value, expected_type, path)
    except TypeError:
        return False


def is_instance(value: typing.Any, expected_type: typing.Any, path: str = "") -> bool:
    if hasattr(expected_type, "__supertype__"):
        return is_instance(value, expected_type.__supertype__, path)
    if isinstance(expected_type, typing.TypeAliasType):
        return is_instance(value, expected_type.__value__, path)

    origin = typing.get_origin(expected_type)

    if origin is None:
        if expected_type is typing.Any:
            return True
        if dataclasses.is_dataclass(expected_type):
            if not isinstance(value, expected_type):  # type: ignore[arg-type]
                _raise_type_error(value, expected_type, path)
            hints = typing.get_type_hints(expected_type)
            for field in dataclasses.fields(expected_type):
                field_value = getattr(value, field.name)
                field_type = hints.get(field.name, typing.Any)
                field_path = f"{path}.{field.name}" if path else field.name
                if not is_instance(field_value, field_type, field_path):
                    return False
            return True
        else:
            if not isinstance(value, expected_type):
                _raise_type_error(value, expected_type, path)
            return True

    args = typing.get_args(expected_type)

    if origin is typing.Union or origin is types.UnionType:
        for arg in args:
            try:
                if is_instance(value, arg, path):
                    return True
            except TypeError:
                continue
        _raise_type_error(value, expected_type, path)
        return False

    if origin in {list, set, tuple}:
        if not isinstance(value, origin):
            _raise_type_error(value, expected_type, path)
        if not args:
            return True
        elem_type = args[0]
        for i, elem in enumerate(value):
            elem_path = f"{path}[{i}]" if path else f"[{i}]"
            if not is_instance(elem, elem_type, elem_path):
                return False
        return True

    if origin is dict:
        if not isinstance(value, dict):
            _raise_type_error(value, expected_type, path)
        key_type, val_type = args
        for k, v in value.items():
            key_path = f"{path}[{k!r}]" if path else f"[{k!r}]"
            if not is_instance(k, key_type, f"{path}.<key>" if path else "<key>"):
                return False
            if not is_instance(v, val_type, key_path):
                return False
        return True

    if origin is typing.Literal:
        if value not in args:
            _raise_type_error(value, expected_type, path)
        return True

    if not isinstance(value, origin):
        _raise_type_error(value, expected_type, path)
    return True


def _raise_type_error(value: typing.Any, expected_type: typing.Any, path: str) -> None:
    location = f"位置 {path}: " if path else ""
    raise TypeError(f"{location}型 {expected_type} を期待しますが、{type(value)} の値が設定されています。(値:{value!r})")
