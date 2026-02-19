"""JSON関連。"""

import base64
import datetime
import json
import pathlib
import typing


def load(
    path: str | pathlib.Path,
    errors: str | None = None,
    strict: bool = False,
    **kwargs,
) -> typing.Any:
    """JSONファイルの読み込み。"""
    path = pathlib.Path(path)
    if path.exists():
        data = loads(path.read_text(encoding="utf-8", errors=errors), **kwargs)
    else:
        if strict:
            raise FileNotFoundError(f"File not found: {path}")
        data = {}
    return data


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
    path: str | pathlib.Path,
    data: typing.Any,
    ensure_ascii: bool = False,
    indent: int | str | None = None,
    separators: tuple[str, str] | None = None,
    sort_keys: bool = False,
    default: typing.Callable[[typing.Any], typing.Any] = converter,
    **kwargs,
) -> None:
    """JSONのファイル保存。

    標準ライブラリと異なりデフォルトでensure_ascii=False、UTF-8で保存する。

    """
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        dumps(
            data,
            ensure_ascii=ensure_ascii,
            indent=indent,
            separators=separators,
            sort_keys=sort_keys,
            default=default,
            **kwargs,
        ),
        encoding="utf-8",
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
