"""テストコード。"""

import pytest

import pytilpack.validator


@pytest.mark.parametrize(
    "value,expected",
    [
        # 有効なメールアドレス
        ("test@example.com", True),
        ("user.name@example.co.jp", True),
        ("user+tag@example.com", True),
        ("a@b.com", True),
        ("test@subdomain.example.com", True),
        # 無効なメールアドレス
        ("", False),
        ("invalid", False),
        ("@example.com", False),
        ("user@", False),
        ("user @example.com", False),
    ],
)
def test_is_email(value: str, expected: bool) -> None:
    """is_emailのテスト。"""
    assert pytilpack.validator.is_email(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        # 有効なURL
        ("http://example.com", True),
        ("https://example.com", True),
        ("https://example.com/path?q=1", True),
        ("http://sub.domain.example.com", True),
        ("https://example.com:8080/path", True),
        # 無効なURL
        ("", False),
        ("example.com", False),
        ("ftp://example.com", False),
        ("://example.com", False),
        ("http://", False),
    ],
)
def test_is_url(value: str, expected: bool) -> None:
    """is_urlのテスト。"""
    assert pytilpack.validator.is_url(value) == expected


@pytest.mark.parametrize(
    "value,pattern,expected",
    [
        ("abc", r"[a-z]+", True),
        ("123", r"\d+", True),
        ("abc", r"\d+", False),
        ("abc123", r"[a-z]+\d+", True),
        ("abc", r"ab", False),  # fullmatchなので部分一致はFalse
    ],
)
def test_is_match(value: str, pattern: str, expected: bool) -> None:
    """is_matchのテスト。"""
    assert pytilpack.validator.is_match(value, pattern) == expected


def test_check_required() -> None:
    """check_requiredのテスト。"""
    # 正常系: 例外が出ないこと
    pytilpack.validator.check_required("hello")
    pytilpack.validator.check_required(0)
    pytilpack.validator.check_required(False)
    pytilpack.validator.check_required([1, 2, 3])

    # 異常系
    with pytest.raises(ValueError):
        pytilpack.validator.check_required(None)
    with pytest.raises(ValueError):
        pytilpack.validator.check_required("")
    with pytest.raises(ValueError):
        pytilpack.validator.check_required([])
    with pytest.raises(ValueError):
        pytilpack.validator.check_required({})


def test_check_length() -> None:
    """check_lengthのテスト。"""
    # 正常系
    pytilpack.validator.check_length("abc", min=1, max=5)
    pytilpack.validator.check_length("a", min=1)
    pytilpack.validator.check_length("abcde", max=5)
    # 境界値
    pytilpack.validator.check_length("abc", min=3, max=3)

    # 異常系: min違反
    with pytest.raises(ValueError):
        pytilpack.validator.check_length("", min=1)
    # 異常系: max違反
    with pytest.raises(ValueError):
        pytilpack.validator.check_length("abcdef", max=5)


def test_check_range() -> None:
    """check_rangeのテスト。"""
    # 正常系
    pytilpack.validator.check_range(5, min=1, max=10)
    pytilpack.validator.check_range(1, min=1)
    pytilpack.validator.check_range(10, max=10)
    # 境界値
    pytilpack.validator.check_range(1.0, min=1.0, max=1.0)
    # floatでも動くこと
    pytilpack.validator.check_range(3.14, min=0.0, max=10.0)

    # 異常系: min違反
    with pytest.raises(ValueError):
        pytilpack.validator.check_range(0, min=1)
    # 異常系: max違反
    with pytest.raises(ValueError):
        pytilpack.validator.check_range(11, max=10)


def test_check_email_url() -> None:
    """check_email/check_urlのテスト。"""
    # 正常系: 例外が出ないこと
    pytilpack.validator.check_email("test@example.com")
    pytilpack.validator.check_url("https://example.com")

    # 異常系
    with pytest.raises(ValueError):
        pytilpack.validator.check_email("invalid")
    with pytest.raises(ValueError):
        pytilpack.validator.check_url("not-a-url")

    # check_patternもテスト
    pytilpack.validator.check_pattern("abc", r"[a-z]+")
    with pytest.raises(ValueError):
        pytilpack.validator.check_pattern("abc", r"\d+")
