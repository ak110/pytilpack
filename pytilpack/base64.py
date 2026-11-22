__lazy_modules__ = ["base64"]

import base64


def encode(s: str | bytes, url_safe: bool = False) -> str:
    b = s.encode("utf-8") if isinstance(s, str) else s
    encoded = base64.urlsafe_b64encode(b) if url_safe else base64.b64encode(b)
    return encoded.decode("ascii")


def decode(s: str, url_safe: bool = False) -> bytes:
    return base64.urlsafe_b64decode(s) if url_safe else base64.b64decode(s)
