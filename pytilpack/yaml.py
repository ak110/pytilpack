"""YAML関連。"""

import pathlib
import typing

import yaml


def load(path: str | pathlib.Path, errors: str | None = None, strict: bool = False, Loader=yaml.SafeLoader) -> typing.Any:
    """YAMLファイルの読み込み。"""
    path = pathlib.Path(path)
    if path.exists():
        with path.open(encoding="utf-8", errors=errors) as f:
            return yaml.load(f, Loader=Loader)
    else:
        if strict:
            raise FileNotFoundError(f"File not found: {path}")
        return {}


def load_all(
    path: str | pathlib.Path, errors: str | None = None, strict: bool = False, Loader=yaml.SafeLoader
) -> list[typing.Any]:
    """YAMLファイルの読み込み。"""
    path = pathlib.Path(path)
    if path.exists():
        with path.open(encoding="utf-8", errors=errors) as f:
            return list(yaml.load_all(f, Loader=Loader))
    else:
        if strict:
            raise FileNotFoundError(f"File not found: {path}")
        return []


class IndentDumper(yaml.SafeDumper):
    """dictの中にlistがあるときのインデントを増やすDumper。

    PyYAMLのデフォルトでは

    ```yaml
    key:
    - item1
    - item2
    ```

    となるが、これを

    ```yaml
    key:
      - item1
      - item2
    ```

    とする。

    """

    @typing.override
    def increase_indent(self, flow=False, indentless=False):
        """インデント増加時の処理。"""
        del indentless
        return super().increase_indent(flow, False)


def save(
    path: str | pathlib.Path,
    data: typing.Any,
    allow_unicode: bool | None = True,
    width: int = 99,
    default_style: str | None = None,
    default_flow_style: bool | None = False,
    sort_keys: bool = False,
    Dumper=IndentDumper,
    **kwargs,
):
    """YAMLのファイル保存。"""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        dumps(
            data,
            allow_unicode=allow_unicode,
            width=width,
            default_style=default_style,
            default_flow_style=default_flow_style,
            sort_keys=sort_keys,
            Dumper=Dumper,
            **kwargs,
        ),
        encoding="utf-8",
    )


def save_all(
    path: str | pathlib.Path,
    data: list[typing.Any],
    allow_unicode: bool | None = True,
    width: int = 99,
    default_style: str | None = None,
    default_flow_style: bool | None = False,
    sort_keys: bool = False,
    Dumper=IndentDumper,
    **kwargs,
):
    """YAMLのファイル保存。"""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        dumps_all(
            data,
            allow_unicode=allow_unicode,
            width=width,
            default_style=default_style,
            default_flow_style=default_flow_style,
            sort_keys=sort_keys,
            Dumper=Dumper,
            **kwargs,
        ),
        encoding="utf-8",
    )


def dumps(
    data: typing.Any,
    allow_unicode: bool | None = True,
    width: int = 99,
    default_style: str | None = None,
    default_flow_style: bool | None = False,
    sort_keys: bool = False,
    Dumper=IndentDumper,
    **kwargs,
) -> str:
    """YAMLの文字列化。"""
    return yaml.dump(
        data,
        allow_unicode=allow_unicode,
        width=width,
        default_style=default_style,
        default_flow_style=default_flow_style,
        sort_keys=sort_keys,
        Dumper=Dumper,
        **kwargs,
    )


def dumps_all(
    data: list[typing.Any],
    allow_unicode: bool | None = True,
    width: int = 99,
    default_style: str | None = None,
    default_flow_style: bool | None = False,
    sort_keys: bool = False,
    Dumper=IndentDumper,
    **kwargs,
) -> str:
    """YAMLの文字列化。"""
    return yaml.dump_all(
        data,
        allow_unicode=allow_unicode,
        width=width,
        default_style=default_style,
        default_flow_style=default_flow_style,
        sort_keys=sort_keys,
        Dumper=Dumper,
        **kwargs,
    )
