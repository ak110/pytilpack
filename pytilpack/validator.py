__lazy_modules__ = ["re", "typing", "urllib.parse"]

import re
import typing
import urllib.parse

# HTML5仕様のメールアドレス正規表現
# https://html.spec.whatwg.org/multipage/input.html#valid-e-mail-address
_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)


def check_required(value: typing.Any) -> None:
    if value is None:
        raise ValueError("値は必須です。")
    if isinstance(value, str) and value == "":
        raise ValueError("値は必須です。")
    if isinstance(value, typing.Sized) and not isinstance(value, str) and len(value) == 0:
        raise ValueError("値は必須です。")


def check_length(  # pylint: disable=redefined-builtin
    value: str, *, min: int | None = None, max: int | None = None
) -> None:
    length = len(value)
    if min is not None and length < min:
        raise ValueError(f"文字列の長さは{min}以上である必要があります。(実際: {length})")
    if max is not None and length > max:
        raise ValueError(f"文字列の長さは{max}以下である必要があります。(実際: {length})")


def check_range(  # pylint: disable=redefined-builtin
    value: int | float,
    *,
    min: int | float | None = None,
    max: int | float | None = None,
) -> None:
    if min is not None and value < min:
        raise ValueError(f"値は{min}以上である必要があります。(実際: {value})")
    if max is not None and value > max:
        raise ValueError(f"値は{max}以下である必要があります。(実際: {value})")


def check_pattern(value: str, pattern: str) -> None:
    if not is_match(value, pattern):
        raise ValueError(f"値がパターン '{pattern}' に一致しません。(実際: {value!r})")


def check_email(value: str) -> None:
    if not is_email(value):
        raise ValueError(f"メールアドレスの形式が不正です。user@example.comの形式で指定する。(実際: {value!r})")


def check_url(value: str) -> None:
    if not is_url(value):
        raise ValueError(f"URLの形式が不正です。http://またはhttps://で始まりホスト名を含む形式で指定する。(実際: {value!r})")


def is_email(value: str) -> bool:
    return _EMAIL_PATTERN.fullmatch(value) is not None


def is_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def is_match(value: str, pattern: str) -> bool:
    return re.fullmatch(pattern, value) is not None
