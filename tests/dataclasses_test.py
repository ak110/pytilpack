"""テストコード。"""

import dataclasses
import pathlib

import pytest

import pytilpack.dataclasses_


@dataclasses.dataclass
class A:
    """テスト用。"""

    a: int
    b: str


@dataclasses.dataclass
class Nested:
    """テスト用。"""

    a: A


@dataclasses.dataclass
class User:
    """テスト用。"""

    id: int
    name: str
    tags: list[str] | None = None
    home: pathlib.Path | None = None


def test_asdict() -> None:
    x = Nested(A(1, "a"))
    assert pytilpack.dataclasses_.asdict(x) == {"a": A(1, "a")}
    assert pytilpack.dataclasses_.asdict(x) != {"a": {"a": 1, "b": "a"}}


def test_json(tmp_path: pathlib.Path) -> None:
    x = Nested(A(1, "a"))
    pytilpack.dataclasses_.tojson(x, tmp_path / "test.json")
    assert pytilpack.dataclasses_.fromjson(Nested, tmp_path / "test.json") == x


def test_validate() -> None:
    """validateのテスト。"""
    # 正常なケース
    user = User(id=1, name="Taro", tags=["dev", "ai"], home=pathlib.Path.home())
    pytilpack.dataclasses_.validate(user)  # 例外は発生しない

    # 型不一致のケース
    user_bad = User(id="oops", name="Taro")  # type: ignore[arg-type]
    with pytest.raises(
        TypeError,
        match="フィールド id は、型 <class 'int'> を期待しますが、<class 'str'> の値が設定されています。",
    ):
        pytilpack.dataclasses_.validate(user_bad)

    # dataclassでないケースのテスト
    with pytest.raises(TypeError, match="is not a dataclass instance"):
        pytilpack.dataclasses_.validate("not a dataclass")  # type: ignore[type-var]
