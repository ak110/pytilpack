"""pycryptodomeを使って簡単にAES-GCM暗号化/復号を行うユーティリティ。

キー及び暗号文はBASE64エンコードした文字列で扱うのを基本とする。

また、nonceはデフォルトで12バイト、暗号文の先頭に付加する前提とする。

"""

import base64
import json
import secrets
import typing

import Crypto.Cipher.AES
import Crypto.Util.Padding

DEFAULT_KEY_SIZE = 32
"""デフォルトのキーサイズ（バイト単位）"""


def create_key(nbytes: int = DEFAULT_KEY_SIZE) -> str:
    """ランダムなキーを生成。デフォルトは32バイト。"""
    return base64.b64encode(secrets.token_bytes(nbytes)).decode("utf-8")


def encrypt_json(obj: typing.Any, key: str | bytes) -> str:
    """JSON化してencrypt()"""
    return encrypt(json.dumps(obj), key)


def decrypt_json(s: str, key: str | bytes) -> typing.Any:
    """decrypt()してJSON読み込み。"""
    return json.loads(decrypt(s, key))


def encrypt(plaintext: str, key: str | bytes) -> str:
    """暗号化。"""
    if isinstance(key, str):
        key = base64.b64decode(key)
    plaintext = plaintext.encode("utf-8")
    nonce = secrets.token_bytes(12)
    cipher = Crypto.Cipher.AES.new(key, Crypto.Cipher.AES.MODE_GCM, nonce=nonce)
    ct, tag = cipher.encrypt_and_digest(plaintext)
    ciphertext = nonce + ct + tag
    ciphertext = base64.b64encode(ciphertext).decode("utf-8")
    return ciphertext


def decrypt(ciphertext: str, key: str | bytes) -> str:
    """復号。"""
    if isinstance(key, str):
        key = base64.b64decode(key)
    cipherbytes = base64.b64decode(ciphertext)
    nonce, ct, tag = cipherbytes[:12], cipherbytes[12:-16], cipherbytes[-16:]
    cipher = Crypto.Cipher.AES.new(key, Crypto.Cipher.AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ct, tag)
    return plaintext.decode("utf-8")
