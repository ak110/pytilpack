"""Base64エンコーディング/デコーディングユーティリティ。"""

import base64


def encode(s: str | bytes) -> str:
    """文字列またはバイト列をBase64エンコードします。

    文字列が与えられた場合、UTF-8としてエンコードされます。

    Args:
        s: エンコードする文字列またはバイト列。

    Returns:
        Base64エンコードされた文字列。
    """
    if isinstance(s, str):
        b = s.encode("utf-8")
    else:
        b = s
    return base64.b64encode(b).decode("ascii")


def decode(s: str) -> bytes:
    """Base64エンコードされた文字列をデコードします。

    Args:
        s: Base64エンコードされた文字列。

    Returns:
        デコードされたバイト列。
    """
    return base64.b64decode(s)
