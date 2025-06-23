"""テストコード。"""

import typing

import pytest

import pytilpack.typing_


@pytest.mark.parametrize(
    "value,expected_type,expected",
    [
        # 基本型
        (1, int, True),
        ("hello", str, True),
        (1.0, float, True),
        (True, bool, True),
        ([1, 2, 3], list, True),
        ({1, 2, 3}, set, True),
        ((1, 2, 3), tuple, True),
        ({"a": 1}, dict, True),
        # 型不一致
        (1, str, False),
        ("hello", int, False),
        ([1, 2, 3], str, False),
        # Optional/Union型
        (1, int | None, True),
        (None, int | None, True),
        ("hello", int | None, False),
        (1, int | str, True),
        ("hello", int | str, True),
        (1.0, int | str, False),
        # リスト型
        ([1, 2, 3], list[int], True),
        (["a", "b", "c"], list[str], True),
        ([1, "a"], list[int], False),
        ([1, "a"], list[str], False),
        ([], list[int], True),  # 空リストは任意の型にマッチ
        # セット型
        ({1, 2, 3}, set[int], True),
        ({"a", "b", "c"}, set[str], True),
        ({1, "a"}, set[int], False),
        (set(), set[int], True),  # 空セットは任意の型にマッチ
        # タプル型
        ((1, 2, 3), tuple[int], True),
        (("a", "b", "c"), tuple[str], True),
        ((1, "a"), tuple[int], False),
        ((), tuple[int], True),  # 空タプルは任意の型にマッチ
        # 辞書型
        ({"a": 1, "b": 2}, dict[str, int], True),
        ({1: "a", 2: "b"}, dict[int, str], True),
        ({"a": 1, "b": "c"}, dict[str, int], False),
        ({}, dict[str, int], True),  # 空辞書は任意の型にマッチ
        # 型引数なし
        ([1, 2, 3], list, True),
        ({1, 2, 3}, set, True),
        ((1, 2, 3), tuple, True),
        ({"a": 1}, dict, True),
    ],
)
def test_is_instance(value: typing.Any, expected_type: type, expected: bool) -> None:
    """is_instanceのテスト。"""
    actual = pytilpack.typing_.is_instance(value, expected_type)
    assert actual == expected


def test_newtype() -> None:
    """NewTypeのテスト。"""
    UserId = typing.NewType("UserId", int)

    # NewTypeは基本型として扱われる
    assert pytilpack.typing_.is_instance(123, UserId) is True
    assert pytilpack.typing_.is_instance("hello", UserId) is False


def test_union_type() -> None:
    """UnionType（| 演算子）のテスト。"""
    # Python 3.10+のUnionType
    union_type = int | str

    assert pytilpack.typing_.is_instance(123, union_type) is True
    assert pytilpack.typing_.is_instance("hello", union_type) is True
    assert pytilpack.typing_.is_instance(1.0, union_type) is False


def test_literal() -> None:
    """Literalのテスト。"""
    # 文字列リテラル
    literal_str = typing.Literal["red", "green", "blue"]
    assert pytilpack.typing_.is_instance("red", literal_str) is True
    assert pytilpack.typing_.is_instance("green", literal_str) is True
    assert pytilpack.typing_.is_instance("blue", literal_str) is True
    assert pytilpack.typing_.is_instance("yellow", literal_str) is False

    # 数値リテラル
    literal_int = typing.Literal[1, 2, 3]
    assert pytilpack.typing_.is_instance(1, literal_int) is True
    assert pytilpack.typing_.is_instance(2, literal_int) is True
    assert pytilpack.typing_.is_instance(3, literal_int) is True
    assert pytilpack.typing_.is_instance(4, literal_int) is False

    # 混合リテラル
    literal_mixed = typing.Literal["active", "inactive", 0, 1]
    assert pytilpack.typing_.is_instance("active", literal_mixed) is True
    assert pytilpack.typing_.is_instance("inactive", literal_mixed) is True
    assert pytilpack.typing_.is_instance(0, literal_mixed) is True
    assert pytilpack.typing_.is_instance(1, literal_mixed) is True
    assert pytilpack.typing_.is_instance("pending", literal_mixed) is False
    assert pytilpack.typing_.is_instance(2, literal_mixed) is False

    # ブールリテラル
    literal_bool = typing.Literal[True, False]
    assert pytilpack.typing_.is_instance(True, literal_bool) is True
    assert pytilpack.typing_.is_instance(False, literal_bool) is True
