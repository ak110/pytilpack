"""テストコード。"""

import dataclasses
import pathlib

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


def test_asdict() -> None:
    x = Nested(A(1, "a"))
    assert pytilpack.dataclasses_.asdict(x) == {"a": A(1, "a")}
    assert pytilpack.dataclasses_.asdict(x) != {"a": {"a": 1, "b": "a"}}


def test_json(tmp_path: pathlib.Path) -> None:
    x = Nested(A(1, "a"))
    pytilpack.dataclasses_.tojson(x, tmp_path / "test.json")
    assert pytilpack.dataclasses_.fromjson(Nested, tmp_path / "test.json") == x
