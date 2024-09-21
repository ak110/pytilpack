"""テストコード。"""

import dataclasses

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


def test_asdict():
    x = Nested(A(1, "a"))
    assert pytilpack.dataclasses_.asdict(x) == {"a": A(1, "a")}
    assert pytilpack.dataclasses_.asdict(x) != {"a": {"a": 1, "b": "a"}}
