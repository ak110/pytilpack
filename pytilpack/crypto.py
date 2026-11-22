__lazy_modules__ = ["base64", "hashlib", "hmac", "json", "struct", "time", "typing"]

import base64
import hashlib
import hmac
import json
import struct
import time
import typing

_VERSION = 0x01
_TYPE_BYTES = 0x00
_TYPE_STR = 0x01
_TYPE_DICT = 0x02
_HMAC_SIZE = 32


class TimestampSigner:
    def __init__(
        self,
        key: str | bytes,
        purpose: str = "",
        get_time: typing.Callable[[], float] = time.time,
    ) -> None:
        key_bytes = key.encode() if isinstance(key, str) else key
        self.derived_key = hmac.new(key_bytes, purpose.encode(), hashlib.sha256).digest()
        self.get_time = get_time

    def sign(self, data: str | bytes | dict) -> str:
        type_byte, payload = _encode_payload(data)

        header = struct.pack(">B", _VERSION) + struct.pack(">d", self.get_time())
        message = header + struct.pack(">B", type_byte) + payload

        sig = hmac.new(self.derived_key, message, hashlib.sha256).digest()
        return _b64url_encode(message + sig)

    def unsign(self, token: str, max_age: float | None = None) -> str | bytes | dict:
        raw = _b64url_decode(token)

        if len(raw) < 1 + 8 + 1 + _HMAC_SIZE:
            raise ValueError("トークンが短すぎます。sign()が返したトークン全体を渡す")

        message = raw[:-_HMAC_SIZE]
        sig = raw[-_HMAC_SIZE:]
        expected = hmac.new(self.derived_key, message, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("署名が一致しません。発行時と同じkey・purposeのTimestampSignerで検証するか、トークンを再発行する")

        version = message[0]
        if version != _VERSION:
            raise ValueError(f"未対応のバージョン: {version}（対応: {_VERSION}）。現在のsign()でトークンを再発行する")

        timestamp = struct.unpack(">d", message[1:9])[0]
        type_byte = message[9]
        payload = message[10:]

        if max_age is not None:
            age = self.get_time() - timestamp
            if age > max_age:
                raise ValueError(
                    f"トークンが期限切れです (経過: {age:.1f}秒、上限: {max_age}秒)。トークンを再発行するか、max_ageを見直す"
                )

        return _decode_payload(type_byte, payload)


def hmac_sign(data: str | bytes, key: str | bytes) -> str:
    data_bytes = data.encode() if isinstance(data, str) else data
    key_bytes = key.encode() if isinstance(key, str) else key
    sig = hmac.new(key_bytes, data_bytes, hashlib.sha256).digest()
    return _b64url_encode(sig)


def hmac_verify(data: str | bytes, signature: str, key: str | bytes) -> bool:
    expected = hmac_sign(data, key)
    return hmac.compare_digest(expected, signature)


def _encode_payload(data: str | bytes | dict) -> tuple[int, bytes]:
    if isinstance(data, dict):
        return _TYPE_DICT, json.dumps(data, ensure_ascii=False).encode()
    if isinstance(data, str):
        return _TYPE_STR, data.encode()
    if isinstance(data, bytes):
        return _TYPE_BYTES, data
    typing.assert_never(data)  # type: ignore[arg-type]


def _decode_payload(type_byte: int, payload: bytes) -> str | bytes | dict:
    if type_byte == _TYPE_DICT:
        return typing.cast(dict, json.loads(payload))
    if type_byte == _TYPE_STR:
        return payload.decode()
    if type_byte == _TYPE_BYTES:
        return payload
    raise ValueError(f"未対応のデータ型: {type_byte}")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)
