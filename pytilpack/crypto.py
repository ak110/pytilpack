"""署名・トークンユーティリティ。

pycrypto.py (AES-GCM暗号化) やsecrets.py (秘密鍵生成) を補完する
HMAC署名・タイムスタンプ付きトークン機能。
"""

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
_HMAC_SIZE = 32  # SHA-256


class TimestampSigner:
    """タイムスタンプ付き署名トークンの生成・検証。"""

    def __init__(self, key: str | bytes, purpose: str = "") -> None:
        """初期化。

        Args:
            key: 署名鍵。
            purpose: 用途識別子。同じ鍵でも異なるpurposeのトークンは互換性がない。
        """
        key_bytes = key.encode() if isinstance(key, str) else key
        # purposeごとに鍵を導出し、用途間の分離を保証
        self._derived_key = hmac.new(key_bytes, purpose.encode(), hashlib.sha256).digest()

    def sign(self, data: str | bytes | dict) -> str:
        """データに署名してトークンを生成する。

        Token format: base64url(version[1] + timestamp[8] + type[1] + data[...] + hmac[32])
        """
        # データ型に応じてtype byteとペイロードを決定
        type_byte, payload = _encode_payload(data)

        # ヘッダ + ペイロードを構築
        header = struct.pack(">B", _VERSION) + struct.pack(">d", time.time())
        message = header + struct.pack(">B", type_byte) + payload

        # HMAC署名を付加
        sig = hmac.new(self._derived_key, message, hashlib.sha256).digest()
        return _b64url_encode(message + sig)

    def unsign(self, token: str, max_age: float | None = None) -> str | bytes | dict:
        """トークンを検証してデータを取り出す。

        Raises:
            ValueError: 検証失敗、期限切れ、バージョン不一致の場合。
        """
        raw = _b64url_decode(token)

        # 最小長チェック: version(1) + timestamp(8) + type(1) + hmac(32) = 42
        if len(raw) < 1 + 8 + 1 + _HMAC_SIZE:
            raise ValueError("トークンが短すぎます")

        # 署名を分離して検証
        message = raw[:-_HMAC_SIZE]
        sig = raw[-_HMAC_SIZE:]
        expected = hmac.new(self._derived_key, message, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("署名が一致しません")

        # ヘッダ解析
        version = message[0]
        if version != _VERSION:
            raise ValueError(f"未対応のバージョン: {version}")

        timestamp = struct.unpack(">d", message[1:9])[0]
        type_byte = message[9]
        payload = message[10:]

        # 有効期限チェック
        if max_age is not None:
            age = time.time() - timestamp
            if age > max_age:
                raise ValueError(f"トークンが期限切れです (経過: {age:.1f}秒)")

        return _decode_payload(type_byte, payload)


def hmac_sign(data: str | bytes, key: str | bytes) -> str:
    """HMAC-SHA256で署名する。

    Returns:
        URL-safe base64エンコードされた署名文字列。
    """
    data_bytes = data.encode() if isinstance(data, str) else data
    key_bytes = key.encode() if isinstance(key, str) else key
    sig = hmac.new(key_bytes, data_bytes, hashlib.sha256).digest()
    return _b64url_encode(sig)


def hmac_verify(data: str | bytes, signature: str, key: str | bytes) -> bool:
    """HMAC-SHA256署名を検証する。タイミングセーフな比較を使用。"""
    expected = hmac_sign(data, key)
    return hmac.compare_digest(expected, signature)


def _encode_payload(data: str | bytes | dict) -> tuple[int, bytes]:
    """データをtype byteとペイロードにエンコードする。"""
    if isinstance(data, dict):
        return _TYPE_DICT, json.dumps(data, ensure_ascii=False).encode()
    if isinstance(data, str):
        return _TYPE_STR, data.encode()
    if isinstance(data, bytes):
        return _TYPE_BYTES, data
    typing.assert_never(data)  # type: ignore[arg-type]


def _decode_payload(type_byte: int, payload: bytes) -> str | bytes | dict:
    """Type byteに基づいてペイロードをデコードする。"""
    if type_byte == _TYPE_DICT:
        return typing.cast(dict, json.loads(payload))
    if type_byte == _TYPE_STR:
        return payload.decode()
    if type_byte == _TYPE_BYTES:
        return payload
    raise ValueError(f"未対応のデータ型: {type_byte}")


def _b64url_encode(data: bytes) -> str:
    """パディングなしのURL-safe base64エンコード。"""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    """パディングなしのURL-safe base64デコード。"""
    # パディングを補完
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)
