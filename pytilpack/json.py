__lazy_modules__ = ["base64", "datetime", "json", "pytilpack.io", "pytilpack.jsonc", "typing"]

import base64
import datetime as dt
import json
import typing

import pytilpack.io
import pytilpack.jsonc


def load(
    source: pytilpack.io.PathOrIO,
    encoding: str = "utf-8",
    errors: str = "replace",
    strict: bool = False,
    **kwargs,
) -> typing.Any:
    try:
        return loads(pytilpack.io.read_text(source, encoding=encoding, errors=errors), **kwargs)
    except FileNotFoundError:
        if strict:
            raise
        return {}


loads = json.loads


def converter(
    o: typing.Any,
    _default: typing.Callable[[typing.Any], typing.Any] | None = None,
) -> typing.Any:
    if isinstance(o, dt.datetime):
        return o.isoformat(timespec="milliseconds")
    if isinstance(o, dt.date):
        return o.isoformat()
    if isinstance(o, dt.time):
        return o.isoformat(timespec="milliseconds")
    if isinstance(o, bytes):
        return base64.b64encode(o).decode("ascii")
    return o if _default is None else _default(o)


def save(
    dest: pytilpack.io.PathOrIO,
    data: typing.Any,
    ensure_ascii: bool = False,
    indent: int | str | None = None,
    separators: tuple[str, str] | None = None,
    sort_keys: bool = False,
    default: typing.Callable[[typing.Any], typing.Any] = converter,
    encoding: str = "utf-8",
    **kwargs,
) -> None:
    pytilpack.io.write_text(
        dest,
        dumps(
            data,
            ensure_ascii=ensure_ascii,
            indent=indent,
            separators=separators,
            sort_keys=sort_keys,
            default=default,
            **kwargs,
        ),
        encoding=encoding,
    )


def dumps(
    data: typing.Any,
    ensure_ascii: bool = False,
    indent: int | str | None = None,
    separators: tuple[str, str] | None = None,
    sort_keys: bool = False,
    default: typing.Callable[[typing.Any], typing.Any] = converter,
    **kwargs,
) -> str:
    return (
        json.dumps(
            data,
            ensure_ascii=ensure_ascii,
            indent=indent,
            separators=separators,
            sort_keys=sort_keys,
            default=default,
            **kwargs,
        )
        + "\n"
    )


def edit(
    text: str,
    updates: typing.Mapping[typing.Sequence[str | int], typing.Any],
    ensure_ascii: bool = False,
    default: typing.Callable[[typing.Any], typing.Any] | None = None,
    **dumps_kwargs: typing.Any,
) -> str:
    return pytilpack.jsonc.edit(text, updates, ensure_ascii=ensure_ascii, default=default, **dumps_kwargs)


def edit_file(
    path: pytilpack.io.PathOrIO,
    updates: typing.Mapping[typing.Sequence[str | int], typing.Any],
    encoding: str = "utf-8",
    errors: str = "replace",
    ensure_ascii: bool = False,
    default: typing.Callable[[typing.Any], typing.Any] | None = None,
    **dumps_kwargs: typing.Any,
) -> None:
    pytilpack.jsonc.edit_file(
        path,
        updates,
        encoding=encoding,
        errors=errors,
        ensure_ascii=ensure_ascii,
        default=default,
        **dumps_kwargs,
    )
