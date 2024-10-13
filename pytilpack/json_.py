"""JSON関連。"""

import base64
import datetime
import json
import pathlib
import typing


def converter(
    o: typing.Any, _default: typing.Callable[[typing.Any], typing.Any] | None = None
):
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


def load(path: str | pathlib.Path) -> dict[str, typing.Any]:
    """JSONファイルの読み込み。"""
    path = pathlib.Path(path)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {}
    return data


def save(
    path: str | pathlib.Path,
    data: dict,
    ensure_ascii=False,
    indent=None,
    separators=None,
    sort_keys=False,
    **kwargs,
):
    """JSONのファイル保存。"""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            data,
            ensure_ascii=ensure_ascii,
            indent=indent,
            separators=separators,
            sort_keys=sort_keys,
            **kwargs,
        )
        + "\n",
        encoding="utf-8",
    )
