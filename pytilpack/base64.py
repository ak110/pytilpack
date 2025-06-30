"""Base64エンコーディング/デコーディングユーティリティ。"""

import base64


def encode(s: str | bytes, url_safe: bool = False) -> str:
    """文字列またはバイト列をBase64エンコードします。

    文字列が与えられた場合、UTF-8としてエンコードされます。

    Args:
        s: エンコードする文字列またはバイト列。
        url_safe: URLセーフなBase64エンコードを使用するかどうか。

    Returns:
        Base64エンコードされた文字列。
    """
    b = s.encode("utf-8") if isinstance(s, str) else s
    encoded = base64.urlsafe_b64encode(b) if url_safe else base64.b64encode(b)
    return encoded.decode("ascii")


def decode(s: str, url_safe: bool = False) -> bytes:
    """Base64エンコードされた文字列をデコードします。

    Args:
        s: Base64エンコードされた文字列。
        url_safe: URLセーフなBase64エンコードを使用しているかどうか。

    Returns:
        デコードされたバイト列。
    """
    return base64.urlsafe_b64decode(s) if url_safe else base64.b64decode(s)
