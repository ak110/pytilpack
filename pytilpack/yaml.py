__lazy_modules__ = ["dataclasses", "pytilpack.io", "typing", "yaml"]

import dataclasses
import typing

import yaml

import pytilpack.io


@dataclasses.dataclass
class _DumpOptions:
    allow_unicode: bool | None = True
    width: int = 99
    default_style: str | None = None
    default_flow_style: bool | None = False
    sort_keys: bool = False
    Dumper: typing.Any = None

    def to_kwargs(self) -> dict[str, typing.Any]:
        return {
            "allow_unicode": self.allow_unicode,
            "width": self.width,
            "default_style": self.default_style,
            "default_flow_style": self.default_flow_style,
            "sort_keys": self.sort_keys,
            "Dumper": self.Dumper,
        }


def load(
    source: pytilpack.io.PathOrIO,
    encoding: str = "utf-8",
    errors: str = "replace",
    strict: bool = False,
    Loader=yaml.SafeLoader,
) -> typing.Any:
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
    try:
        return list(yaml.load_all(pytilpack.io.read_text(source, encoding=encoding, errors=errors), Loader=Loader))
    except FileNotFoundError:
        if strict:
            raise
        return []


class CustomDumper(yaml.SafeDumper):
    @typing.override
    def increase_indent(self, flow=False, indentless=False):
        del indentless
        return super().increase_indent(flow, False)

    @staticmethod
    def str_representer(dumper, value):
        if "\n" in value.rstrip():
            return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", value)


CustomDumper.add_representer(str, CustomDumper.str_representer)


def _build_dump_options(
    allow_unicode: bool | None,
    width: int,
    default_style: str | None,
    default_flow_style: bool | None,
    sort_keys: bool,
    Dumper: typing.Any,
) -> _DumpOptions:
    return _DumpOptions(
        allow_unicode=allow_unicode,
        width=width,
        default_style=default_style,
        default_flow_style=default_flow_style,
        sort_keys=sort_keys,
        Dumper=Dumper,
    )


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
    options = _build_dump_options(allow_unicode, width, default_style, default_flow_style, sort_keys, Dumper)
    pytilpack.io.write_text(
        dest,
        yaml.dump(data, **options.to_kwargs(), **kwargs),
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
    options = _build_dump_options(allow_unicode, width, default_style, default_flow_style, sort_keys, Dumper)
    pytilpack.io.write_text(
        dest,
        yaml.dump_all(data, **options.to_kwargs(), **kwargs),
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
    options = _build_dump_options(allow_unicode, width, default_style, default_flow_style, sort_keys, Dumper)
    return yaml.dump(data, **options.to_kwargs(), **kwargs)


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
    options = _build_dump_options(allow_unicode, width, default_style, default_flow_style, sort_keys, Dumper)
    return yaml.dump_all(data, **options.to_kwargs(), **kwargs)
