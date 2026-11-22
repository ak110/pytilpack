import dataclasses
import json
import pathlib
import typing

import pytest

import pytilpack.dataclasses


@dataclasses.dataclass
class A:
    a: int
    b: str


@dataclasses.dataclass
class Nested:
    a: A


@dataclasses.dataclass
class ForwardRef:
    child: "A"


StrType = typing.NewType("StrType", str)
IntType = typing.NewType("IntType", int)


@dataclasses.dataclass
class User:
    id: int
    name: str
    tags: list[str] | None = None
    home: pathlib.Path | None = None


@dataclasses.dataclass
class UserWithNewType:
    id: IntType
    name: StrType


def test_fromdict_forward_ref() -> None:
    data = {"child": {"a": 1, "b": "hello"}}
    result = pytilpack.dataclasses.fromdict(ForwardRef, data)
    assert isinstance(result.child, A)
    assert result.child.a == 1
    assert result.child.b == "hello"


def test_asdict() -> None:
    x = Nested(A(1, "a"))
    assert pytilpack.dataclasses.asdict(x) == {"a": A(1, "a")}
    assert pytilpack.dataclasses.asdict(x) != {"a": {"a": 1, "b": "a"}}


def test_json(tmp_path: pathlib.Path) -> None:
    x = Nested(A(1, "a"))
    output = tmp_path / "output.json"
    pytilpack.dataclasses.tojson(x, output)
    assert json.loads(output.read_text(encoding="utf-8")) == {"a": {"a": 1, "b": "a"}}

    source = tmp_path / "input.json"
    source.write_text('{"a": {"a": 1, "b": "a"}}', encoding="utf-8")
    assert pytilpack.dataclasses.fromjson(Nested, source) == x


def test_validate() -> None:
    user = User(id=1, name="Taro", tags=["dev", "ai"], home=pathlib.Path.home())
    pytilpack.dataclasses.validate(user)

    user_bad = User(id="oops", name="Taro")  # type: ignore[arg-type]
    with pytest.raises(
        TypeError,
        match=r"位置 id: 型 <class 'int'> を期待しますが、<class 'str'> の値が設定されています。",
    ):
        pytilpack.dataclasses.validate(user_bad)

    with pytest.raises(TypeError, match="is not a dataclass instance"):
        pytilpack.dataclasses.validate("not a dataclass")  # type: ignore[arg-type]


def test_validate_newtype() -> None:
    user = UserWithNewType(id=IntType(1), name=StrType("Taro"))
    pytilpack.dataclasses.validate(user)

    user_bad = UserWithNewType(id="oops", name="Taro")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"位置 id: 型.*int.*str"):
        pytilpack.dataclasses.validate(user_bad)
