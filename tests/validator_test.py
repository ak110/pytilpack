import pytest

import pytilpack.validator


@pytest.mark.parametrize(
    "value,expected",
    [
        ("test@example.com", True),
        ("user.name@example.co.jp", True),
        ("user+tag@example.com", True),
        ("a@b.com", True),
        ("test@subdomain.example.com", True),
        ("", False),
        ("invalid", False),
        ("@example.com", False),
        ("user@", False),
        ("user @example.com", False),
    ],
)
def test_is_email(value: str, expected: bool) -> None:
    assert pytilpack.validator.is_email(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        ("http://example.com", True),
        ("https://example.com", True),
        ("https://example.com/path?q=1", True),
        ("http://sub.domain.example.com", True),
        ("https://example.com:8080/path", True),
        ("", False),
        ("example.com", False),
        ("ftp://example.com", False),
        ("://example.com", False),
        ("http://", False),
    ],
)
def test_is_url(value: str, expected: bool) -> None:
    assert pytilpack.validator.is_url(value) == expected


@pytest.mark.parametrize(
    "value,pattern,expected",
    [
        ("abc", r"[a-z]+", True),
        ("123", r"\d+", True),
        ("abc", r"\d+", False),
        ("abc123", r"[a-z]+\d+", True),
        ("abc", r"ab", False),
    ],
)
def test_is_match(value: str, pattern: str, expected: bool) -> None:
    assert pytilpack.validator.is_match(value, pattern) == expected


def test_check_required() -> None:
    pytilpack.validator.check_required("hello")
    pytilpack.validator.check_required(0)
    pytilpack.validator.check_required(False)
    pytilpack.validator.check_required([1, 2, 3])

    with pytest.raises(ValueError):
        pytilpack.validator.check_required(None)
    with pytest.raises(ValueError):
        pytilpack.validator.check_required("")
    with pytest.raises(ValueError):
        pytilpack.validator.check_required([])
    with pytest.raises(ValueError):
        pytilpack.validator.check_required({})


def test_check_length() -> None:
    pytilpack.validator.check_length("abc", min=1, max=5)
    pytilpack.validator.check_length("a", min=1)
    pytilpack.validator.check_length("abcde", max=5)
    pytilpack.validator.check_length("abc", min=3, max=3)

    with pytest.raises(ValueError):
        pytilpack.validator.check_length("", min=1)
    with pytest.raises(ValueError):
        pytilpack.validator.check_length("abcdef", max=5)


def test_check_range() -> None:
    pytilpack.validator.check_range(5, min=1, max=10)
    pytilpack.validator.check_range(1, min=1)
    pytilpack.validator.check_range(10, max=10)
    pytilpack.validator.check_range(1.0, min=1.0, max=1.0)
    pytilpack.validator.check_range(3.14, min=0.0, max=10.0)

    with pytest.raises(ValueError):
        pytilpack.validator.check_range(0, min=1)
    with pytest.raises(ValueError):
        pytilpack.validator.check_range(11, max=10)


def test_check_email_url() -> None:
    pytilpack.validator.check_email("test@example.com")
    pytilpack.validator.check_url("https://example.com")

    with pytest.raises(ValueError):
        pytilpack.validator.check_email("invalid")
    with pytest.raises(ValueError):
        pytilpack.validator.check_url("not-a-url")

    pytilpack.validator.check_pattern("abc", r"[a-z]+")
    with pytest.raises(ValueError):
        pytilpack.validator.check_pattern("abc", r"\d+")


def test_check_format_messages() -> None:
    with pytest.raises(ValueError, match="user@example.comの形式で指定する"):
        pytilpack.validator.check_email("x")
    with pytest.raises(ValueError, match="http://またはhttps://で始まりホスト名を含む形式で指定する"):
        pytilpack.validator.check_url("x")
