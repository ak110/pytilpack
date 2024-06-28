"""YAML関連。"""

import pathlib
import typing

import yaml


def load(path: str | pathlib.Path) -> dict[str, typing.Any]:
    """YAMLファイルの読み込み。"""
    path = pathlib.Path(path)
    if path.exists():
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    else:
        data = {}
    return data


def save(
    path: str | pathlib.Path,
    data: dict,
    allow_unicode: bool | None = True,
    default_style: str | None = None,
    default_flow_style: bool | None = False,
    sort_keys: bool = False,
    **kwargs,
):
    """YAMLのファイル保存。"""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            default_style=default_style,
            default_flow_style=default_flow_style,
            allow_unicode=allow_unicode,
            encoding="utf-8",
            sort_keys=sort_keys,
            **kwargs,
        )
