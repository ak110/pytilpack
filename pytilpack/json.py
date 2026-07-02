"""JSON関連。"""

import base64
import datetime
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
    """JSONファイルの読み込み。"""
    try:
        return loads(pytilpack.io.read_text(source, encoding=encoding, errors=errors), **kwargs)
    except FileNotFoundError:
        if strict:
            raise
        return {}


loads = json.loads
"""JSONの文字列解析。標準ライブラリのエイリアス。"""


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

    標準ライブラリと異なりデフォルトでensure_ascii=False。
    日付やbytesを変換するconverter関数をdefault引数に指定する。

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


def edit(
    text: str,
    updates: typing.Mapping[typing.Sequence[str | int], typing.Any],
    ensure_ascii: bool = False,
    default: typing.Callable[[typing.Any], typing.Any] | None = None,
    **dumps_kwargs: typing.Any,
) -> str:
    """JSON文字列中の指定パスの値を書き換えつつ空行・インデントを維持する。

    実装は`pytilpack.jsonc.edit`を再利用する。JSONはJSONCの部分集合であり、
    コメント・trailing commaを含まない入力に対しても同じ位置追跡ロジックで安全に動作する。

    詳細は`pytilpack.jsonc.edit`のdocstringを参照。

    """
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
    """JSONファイルを`edit`で書き換えて上書き保存する。"""
    pytilpack.jsonc.edit_file(
        path,
        updates,
        encoding=encoding,
        errors=errors,
        ensure_ascii=ensure_ascii,
        default=default,
        **dumps_kwargs,
    )
