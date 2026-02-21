"""JSON関連。"""

import base64
import datetime
import json
import typing

import pytilpack.io


def load(
    source: pytilpack.io.PathOrIO,
    encoding: str = "utf-8",
    errors: str = "replace",
    strict: bool = False,
    **kwargs,
) -> typing.Any:
    """JSONファイルの読み込み。"""
    try:
        return loads(pytilpack.io.read_text(source, encoding=encoding, errors=errors), **kwargs)
    except FileNotFoundError:
        if strict:
            raise
        return {}


loads = json.loads
"""JSONの文字列解析。標準ライブラリと同じだけど一応エイリアスを用意しておく。"""


def converter(
    o: typing.Any,
    _default: typing.Callable[[typing.Any], typing.Any] | None = None,
) -> typing.Any:
    """JSONエンコード時の変換処理。

    日付はJavaScriptで対応できるようにISO8601形式に変換する。
    YYYY-MM-DDTHH:mm:ss.sssZ
    <https://tc39.es/ecma262/#sec-date-time-string-format>

    bytesはBASE64エンコードする。

    """
    if isinstance(o, datetime.datetime):
        return o.isoformat(timespec="milliseconds")
    if isinstance(o, datetime.date):
        return o.isoformat()
    if isinstance(o, datetime.time):
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
    """JSONのファイル保存。

    標準ライブラリと異なりデフォルトでensure_ascii=False、UTF-8で保存する。

    """
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
    """JSONの文字列化。

    標準ライブラリと異なりデフォルトでensure_ascii=False、UTF-8で保存する。
    また、日付やbytesを変換するためのconverter関数をdefault引数に指定している。

    """
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
