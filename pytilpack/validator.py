"""HTML input属性ライクなバリデーション用ユーティリティ。"""

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


# --- check_* 関数 (違反時にValueErrorを送出) ---


def check_required(value: typing.Any) -> None:
    """値が必須であることを検証する。

    None、空文字列、長さ0のコレクションの場合にValueErrorを送出する。
    HTMLのrequired属性に相当。
    """
    if value is None:
        raise ValueError("値は必須です。")
    if isinstance(value, str) and value == "":
        raise ValueError("値は必須です。")
    if isinstance(value, typing.Sized) and not isinstance(value, str) and len(value) == 0:
        raise ValueError("値は必須です。")


def check_length(  # pylint: disable=redefined-builtin
    value: str, *, min: int | None = None, max: int | None = None
) -> None:
    """文字列の長さを検証する。

    HTMLのminlength/maxlength属性に相当。
    """
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
    """数値の範囲を検証する。

    HTMLのmin/max属性に相当。
    """
    if min is not None and value < min:
        raise ValueError(f"値は{min}以上である必要があります。(実際: {value})")
    if max is not None and value > max:
        raise ValueError(f"値は{max}以下である必要があります。(実際: {value})")


def check_pattern(value: str, pattern: str) -> None:
    """文字列がパターンに一致することを検証する。

    HTMLのpattern属性に相当(fullmatchセマンティクス)。
    """
    if not is_match(value, pattern):
        raise ValueError(f"値がパターン '{pattern}' に一致しません。(実際: {value!r})")


def check_email(value: str) -> None:
    """メールアドレスの形式を検証する。"""
    if not is_email(value):
        raise ValueError(f"メールアドレスの形式が不正です。(実際: {value!r})")


def check_url(value: str) -> None:
    """URLの形式を検証する。"""
    if not is_url(value):
        raise ValueError(f"URLの形式が不正です。(実際: {value!r})")


# --- is_* 関数 (判定してboolを返す) ---


def is_email(value: str) -> bool:
    """メールアドレスの形式を判定する。HTML5のtype="email"相当。"""
    return _EMAIL_PATTERN.fullmatch(value) is not None


def is_url(value: str) -> bool:
    """URLの形式を判定する。HTML5のtype="url"相当。"""
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def is_match(value: str, pattern: str) -> bool:
    """文字列がパターンに完全一致するか判定する。HTMLのpattern属性相当。"""
    return re.fullmatch(pattern, value) is not None
