"""JSON関連。"""

import json
import pathlib
import typing


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
