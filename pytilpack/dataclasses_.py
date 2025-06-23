"""dataclasses関連のユーティリティ。"""

import dataclasses
import pathlib
import typing

import pytilpack.json_
import pytilpack.typing_

# https://stackoverflow.com/questions/77071473/where-can-i-import-dataclassinstance-for-mypy-check
if typing.TYPE_CHECKING:
    from _typeshed import DataclassInstance

    TDataClass = typing.TypeVar("TDataClass", bound=DataclassInstance)


def asdict(obj: typing.Any) -> dict[str, typing.Any]:
    """dataclasses.asdict()のシャローコピーバージョン。

    dataclasses.asdict()はネストされたdataclassを再帰的に処理してしまうが、
    その挙動が要らない場合に使う。
    公式マニュアルに書いてある回避策そのままのコード。
    <https://docs.python.org/ja/3/library/dataclasses.html#dataclasses.asdict>

    """
    return {field.name: getattr(obj, field.name) for field in dataclasses.fields(obj)}


def fromdict(cls: "type[TDataClass]", data: dict[str, typing.Any]) -> "TDataClass":
    """dictからdataclassを生成する。

    pytilpack.dataclasses_.asdict()ではなく、
    dataclasses.asdict()の逆変換(ネストにも対応)。

    Args:
        cls: dataclassの型
        data: dict

    Returns:
        dataclassのインスタンス

    """
    # dataclassのフィールドを取得
    field_types = {f.name: f.type for f in dataclasses.fields(cls)}
    # dataclassのフィールドに対応する値を取得
    values: dict[str, typing.Any] = {}
    for k, v in data.items():
        if v is None:
            # 値がNoneの場合はスキップ
            continue
        if k in field_types:
            # フィールドの型がdataclassの場合
            if dataclasses.is_dataclass(field_types[k]):
                # 再帰的にfromdictを呼び出す
                values[k] = fromdict(field_types[k], v)  # type: ignore[arg-type]
            else:
                values[k] = v
    # dataclassのインスタンスを生成
    return cls(**values)


def fromjson(cls: "type[TDataClass]", json_path: str | pathlib.Path) -> "TDataClass":
    """jsonからdataclassを生成する。

    Args:
        cls: dataclassの型
        json: json

    Returns:
        dataclassのインスタンス

    """
    return fromdict(cls, pytilpack.json_.load(json_path))


def tojson(
    obj: typing.Any,
    json_path: str | pathlib.Path,
    ensure_ascii: bool = False,
    indent: typing.Any | None = None,
    separators: typing.Any | None = None,
    sort_keys: bool = False,
) -> None:
    """dataclassをjsonに変換して保存する。

    Args:
        obj: dataclassのインスタンス
        json_path: 保存先のパス

    """
    pytilpack.json_.save(
        json_path,
        dataclasses.asdict(obj),
        ensure_ascii=ensure_ascii,
        indent=indent,
        separators=separators,
        sort_keys=sort_keys,
    )


def validate(instance: "TDataClass") -> None:
    """dataclassインスタンスのフィールド型を簡易チェックする。

    Raises:
        TypeError: 型不一致、またはdataclassでない場合。
    """
    if not dataclasses.is_dataclass(instance):
        raise TypeError(f"{instance!r} is not a dataclass instance")

    hints = typing.get_type_hints(instance.__class__)
    for field in dataclasses.fields(instance):
        expected = hints.get(field.name, typing.Any)
        actual = getattr(instance, field.name)
        if not pytilpack.typing_.is_instance(actual, expected):
            raise TypeError(
                f"フィールド {field.name} は、型 {expected} を期待しますが、"
                f"{type(actual)} の値が設定されています。(値:{actual!r})"
            )
