"""テストコード。"""

import dataclasses
import pathlib
import typing

import pytest

import pytilpack.dataclasses


@dataclasses.dataclass
class A:
    """テスト用。"""

    a: int
    b: str


@dataclasses.dataclass
class Nested:
    """テスト用。"""

    a: A


# NewType for testing
StrType = typing.NewType("StrType", str)
IntType = typing.NewType("IntType", int)


@dataclasses.dataclass
class User:
    """テスト用。"""

    id: int
    name: str
    tags: list[str] | None = None
    home: pathlib.Path | None = None


@dataclasses.dataclass
class UserWithNewType:
    """NewType用テスト。"""

    id: IntType
    name: StrType


def test_asdict() -> None:
    x = Nested(A(1, "a"))
    assert pytilpack.dataclasses.asdict(x) == {"a": A(1, "a")}
    assert pytilpack.dataclasses.asdict(x) != {"a": {"a": 1, "b": "a"}}


def test_json(tmp_path: pathlib.Path) -> None:
    x = Nested(A(1, "a"))
    pytilpack.dataclasses.tojson(x, tmp_path / "test.json")
    assert pytilpack.dataclasses.fromjson(Nested, tmp_path / "test.json") == x


def test_validate() -> None:
    """validateのテスト。"""
    # 正常なケース
    user = User(id=1, name="Taro", tags=["dev", "ai"], home=pathlib.Path.home())
    pytilpack.dataclasses.validate(user)  # 例外は発生しない

    # 型不一致のケース
    user_bad = User(id="oops", name="Taro")  # type: ignore[arg-type]
    with pytest.raises(
        TypeError,
        match=r"位置 id: 型 <class 'int'> を期待しますが、<class 'str'> の値が設定されています。",
    ):
        pytilpack.dataclasses.validate(user_bad)

    # dataclassでないケースのテスト
    with pytest.raises(TypeError, match="is not a dataclass instance"):
        pytilpack.dataclasses.validate("not a dataclass")  # type: ignore[arg-type]


def test_validate_newtype() -> None:
    """NewTypeに対するvalidateのテスト。"""
    # 正常なケース - NewTypeは基底型と同じ値で通る
    user = UserWithNewType(id=IntType(1), name=StrType("Taro"))
    pytilpack.dataclasses.validate(user)  # 例外は発生しない

    # 基底型の値でも通る（NewTypeは実行時には基底型と同じ）
    user2 = UserWithNewType(id=1, name="Taro")  # type: ignore[arg-type]
    pytilpack.dataclasses.validate(user2)  # 例外は発生しない

    # 型不一致のケース
    user_bad = UserWithNewType(id="oops", name="Taro")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"位置 id: 型.*int.*str"):
        pytilpack.dataclasses.validate(user_bad)
