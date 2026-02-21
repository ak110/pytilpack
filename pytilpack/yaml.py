"""YAML関連。"""

import typing

import yaml

import pytilpack.io


def load(
    source: pytilpack.io.PathOrIO,
    encoding: str = "utf-8",
    errors: str = "replace",
    strict: bool = False,
    Loader=yaml.SafeLoader,
) -> typing.Any:
    """YAMLファイルの読み込み。"""
    try:
        return yaml.load(pytilpack.io.read_text(source, encoding=encoding, errors=errors), Loader=Loader)
    except FileNotFoundError:
        if strict:
            raise
        return {}


def load_all(
    source: pytilpack.io.PathOrIO,
    encoding: str = "utf-8",
    errors: str = "replace",
    strict: bool = False,
    Loader=yaml.SafeLoader,
) -> list[typing.Any]:
    """YAMLファイルの読み込み。"""
    try:
        return list(yaml.load_all(pytilpack.io.read_text(source, encoding=encoding, errors=errors), Loader=Loader))
    except FileNotFoundError:
        if strict:
            raise
        return []


class CustomDumper(yaml.SafeDumper):
    """書式をカスタマイズしたDumper。

    インデントのカスタマイズ:

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

    文字列のカスタマイズ:

    2行以上の文字列はブロックスカラーで出力する。

    """

    @typing.override
    def increase_indent(self, flow=False, indentless=False):
        """インデント増加時の処理。"""
        del indentless
        return super().increase_indent(flow, False)

    @staticmethod
    def str_representer(dumper, value):
        """改行を含む文字列を検出し、style='|' で出力する representer。"""
        if "\n" in value.rstrip():
            # 改行を含む場合はリテラルスタイル '|'
            return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")
        # 改行を含まない場合は既定動作
        return dumper.represent_scalar("tag:yaml.org,2002:str", value)


CustomDumper.add_representer(str, CustomDumper.str_representer)


def save(
    dest: pytilpack.io.PathOrIO,
    data: typing.Any,
    allow_unicode: bool | None = True,
    width: int = 99,
    default_style: str | None = None,
    default_flow_style: bool | None = False,
    sort_keys: bool = False,
    Dumper=CustomDumper,
    encoding: str = "utf-8",
    **kwargs,
) -> None:
    """YAMLのファイル保存。"""
    pytilpack.io.write_text(
        dest,
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
        encoding=encoding,
    )


def save_all(
    dest: pytilpack.io.PathOrIO,
    data: list[typing.Any],
    allow_unicode: bool | None = True,
    width: int = 99,
    default_style: str | None = None,
    default_flow_style: bool | None = False,
    sort_keys: bool = False,
    Dumper=CustomDumper,
    encoding: str = "utf-8",
    **kwargs,
) -> None:
    """YAMLのファイル保存。"""
    pytilpack.io.write_text(
        dest,
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
        encoding=encoding,
    )


def dumps(
    data: typing.Any,
    allow_unicode: bool | None = True,
    width: int = 99,
    default_style: str | None = None,
    default_flow_style: bool | None = False,
    sort_keys: bool = False,
    Dumper=CustomDumper,
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
    Dumper=CustomDumper,
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
