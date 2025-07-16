"""テストコード。"""

import typing

import pytest

import pytilpack.typing

type StrLiteralAlias = typing.Literal["red", "green", "blue"]
type NumberLiteralAlias = typing.Literal[1, 2, 3]
type MixedLiteralAlias = typing.Literal["active", "inactive", 0, 1]
type StrNumberLiteralAlias = StrLiteralAlias | NumberLiteralAlias


@pytest.mark.parametrize(
    "t,expected",
    [
        (typing.Literal["red", "green", "blue"], ["red", "green", "blue"]),
        (typing.Literal[1, 2, 3], [1, 2, 3]),
        (typing.Literal["active", "inactive", 0, 1], ["active", "inactive", 0, 1]),
        (StrLiteralAlias, ["red", "green", "blue"]),
        (NumberLiteralAlias, [1, 2, 3]),
        (MixedLiteralAlias, ["active", "inactive", 0, 1]),
        (typing.Literal["red", "green", "blue"] | typing.Literal[1, 2, 3], ["red", "green", "blue", 1, 2, 3]),
        (StrLiteralAlias | NumberLiteralAlias, ["red", "green", "blue", 1, 2, 3]),
        (StrNumberLiteralAlias, ["red", "green", "blue", 1, 2, 3]),
    ],
)
def test_get_literal_values(t, expected) -> None:
    """Literalの値を取得するテスト。"""
    assert pytilpack.typing.get_literal_values(t) == expected


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
    actual = pytilpack.typing.is_instance_safe(value, expected_type)
    assert actual == expected


def test_newtype() -> None:
    """NewTypeのテスト。"""
    UserId = typing.NewType("UserId", int)

    # NewTypeは基本型として扱われる
    assert pytilpack.typing.is_instance_safe(123, UserId) is True
    assert pytilpack.typing.is_instance_safe("hello", UserId) is False


def test_union_type() -> None:
    """UnionType（| 演算子）のテスト。"""
    # Python 3.10+のUnionType
    union_type = int | str

    assert pytilpack.typing.is_instance_safe(123, union_type) is True
    assert pytilpack.typing.is_instance_safe("hello", union_type) is True
    assert pytilpack.typing.is_instance_safe(1.0, union_type) is False


def test_literal() -> None:
    """Literalのテスト。"""
    # 文字列リテラル
    literal_str = typing.Literal["red", "green", "blue"]
    assert pytilpack.typing.is_instance_safe("red", literal_str) is True
    assert pytilpack.typing.is_instance_safe("green", literal_str) is True
    assert pytilpack.typing.is_instance_safe("blue", literal_str) is True
    assert pytilpack.typing.is_instance_safe("yellow", literal_str) is False

    # 数値リテラル
    literal_int = typing.Literal[1, 2, 3]
    assert pytilpack.typing.is_instance_safe(1, literal_int) is True
    assert pytilpack.typing.is_instance_safe(2, literal_int) is True
    assert pytilpack.typing.is_instance_safe(3, literal_int) is True
    assert pytilpack.typing.is_instance_safe(4, literal_int) is False

    # 混合リテラル
    literal_mixed = typing.Literal["active", "inactive", 0, 1]
    assert pytilpack.typing.is_instance_safe("active", literal_mixed) is True
    assert pytilpack.typing.is_instance_safe("inactive", literal_mixed) is True
    assert pytilpack.typing.is_instance_safe(0, literal_mixed) is True
    assert pytilpack.typing.is_instance_safe(1, literal_mixed) is True
    assert pytilpack.typing.is_instance_safe("pending", literal_mixed) is False
    assert pytilpack.typing.is_instance_safe(2, literal_mixed) is False

    # ブールリテラル
    literal_bool = typing.Literal[True, False]
    assert pytilpack.typing.is_instance_safe(True, literal_bool) is True
    assert pytilpack.typing.is_instance_safe(False, literal_bool) is True


def test_dataclass() -> None:
    """dataclassのテスト。"""
    import dataclasses

    @dataclasses.dataclass
    class Person:
        """テスト用データクラス。"""

        name: str
        age: int
        tags: list[str]

    @dataclasses.dataclass
    class Company:
        """テスト用データクラス。"""

        name: str
        employees: list[Person]

    # 正常ケース
    person = Person("Alice", 30, ["developer", "python"])
    assert pytilpack.typing.is_instance_safe(person, Person) is True

    company = Company("Tech Corp", [person])
    assert pytilpack.typing.is_instance_safe(company, Company) is True

    # 型不一致ケース（is_instance_safeを使用）
    invalid_person = Person("Bob", "not_int", ["tag"])  # type: ignore[arg-type]
    assert pytilpack.typing.is_instance_safe(invalid_person, Person) is False

    # エラー位置のテスト（is_instanceを使用）
    with pytest.raises(TypeError, match=r"位置 age:.*int.*str"):
        pytilpack.typing.is_instance(invalid_person, Person)

    # ネストしたdataclassのエラー位置テスト
    invalid_company = Company("Bad Corp", [invalid_person])
    with pytest.raises(TypeError, match=r"位置 employees\[0\]\.age:.*int.*str"):
        pytilpack.typing.is_instance(invalid_company, Company)


def test_error_path() -> None:
    """エラーパスのテスト。"""
    # リストのエラー
    with pytest.raises(TypeError, match=r"位置 \[1\]:.*int.*str"):
        pytilpack.typing.is_instance([1, "hello", 3], list[int])

    # 辞書のエラー
    with pytest.raises(TypeError, match=r"位置 \['key2'\]:.*int.*str"):
        pytilpack.typing.is_instance({"key1": 1, "key2": "hello"}, dict[str, int])

    # ネストしたリストのエラー
    with pytest.raises(TypeError, match=r"位置 \[1\]\[0\]:.*int.*str"):
        pytilpack.typing.is_instance([[1, 2], ["hello", 4]], list[list[int]])

    # 複雑なネストのエラー
    data = {"items": [[1, 2], [3, "invalid"]]}
    with pytest.raises(TypeError, match=r"位置 \['items'\]\[1\]\[1\]:.*int.*str"):
        pytilpack.typing.is_instance(data, dict[str, list[list[int]]])
