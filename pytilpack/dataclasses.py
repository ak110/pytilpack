__lazy_modules__ = ["dataclasses", "pathlib", "pytilpack.json", "pytilpack.typing", "typing"]

import dataclasses
import pathlib
import typing

import pytilpack.json
import pytilpack.typing

# https://stackoverflow.com/questions/77071473/where-can-i-import-dataclassinstance-for-mypy-check
if typing.TYPE_CHECKING:
    from _typeshed import DataclassInstance  # noqa: TID254  # 型チェック専用で実行時に読み込まれないため列挙しない

    TDataClass = typing.TypeVar("TDataClass", bound=DataclassInstance)


# 公式ドキュメントの回避策をそのまま実装する。
# https://docs.python.org/ja/3/library/dataclasses.html#dataclasses.asdict
def asdict(obj: typing.Any) -> dict[str, typing.Any]:
    return {field.name: getattr(obj, field.name) for field in dataclasses.fields(obj)}


def fromdict(cls: "type[TDataClass]", data: dict[str, typing.Any]) -> "TDataClass":
    # get_type_hints()を使うことで前方参照（文字列）も解決した実際の型を得る。
    # f.typeは前方参照の場合に文字列のまま返るため、dataclasses.is_dataclass()が常にFalseになるバグを回避する。
    field_types = typing.get_type_hints(cls)
    values: dict[str, typing.Any] = {}
    for k, v in data.items():
        if v is None:
            continue
        if k in field_types:
            if dataclasses.is_dataclass(field_types[k]):
                values[k] = fromdict(field_types[k], v)  # type: ignore[arg-type]
            else:
                values[k] = v
    return cls(**values)


def fromjson(cls: "type[TDataClass]", json_path: str | pathlib.Path) -> "TDataClass":
    return fromdict(cls, pytilpack.json.load(json_path))


def tojson(
    obj: typing.Any,
    json_path: str | pathlib.Path,
    ensure_ascii: bool = False,
    indent: typing.Any | None = None,
    separators: typing.Any | None = None,
    sort_keys: bool = False,
) -> None:
    pytilpack.json.save(
        json_path,
        dataclasses.asdict(obj),
        ensure_ascii=ensure_ascii,
        indent=indent,
        separators=separators,
        sort_keys=sort_keys,
    )


def validate(instance: "DataclassInstance") -> None:
    if not dataclasses.is_dataclass(instance):
        raise TypeError(f"{instance!r} is not a dataclass instance")

    pytilpack.typing.is_instance(instance, instance.__class__)
