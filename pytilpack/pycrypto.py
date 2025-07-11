"""pycryptodomeを使って簡単にAES-GCM暗号化/復号を行うユーティリティ。

キー及び暗号文はBASE64エンコードした文字列で扱うのを基本とする。

また、nonceはデフォルトで12バイト、暗号文の先頭に付加する前提とする。

"""

import json
import secrets
import typing

import Crypto.Cipher.AES

import pytilpack.base64

DEFAULT_KEY_SIZE = 32
"""デフォルトのキーサイズ（バイト単位）"""


def create_key(nbytes: int = DEFAULT_KEY_SIZE, url_safe: bool = False) -> str:
    """ランダムなキーを生成。デフォルトは32バイト。"""
    return pytilpack.base64.encode(secrets.token_bytes(nbytes), url_safe=url_safe)


def encrypt_json(obj: typing.Any, key: str | bytes, url_safe: bool = False) -> str:
    """JSON化してencrypt()"""
    return encrypt(json.dumps(obj), key, url_safe=url_safe)


def decrypt_json(s: str, key: str | bytes, url_safe: bool = False) -> typing.Any:
    """decrypt()してJSON読み込み。"""
    return json.loads(decrypt(s, key, url_safe=url_safe))


def encrypt(plaintext: str, key: str | bytes, url_safe: bool = False) -> str:
    """暗号化。"""
    if isinstance(key, str):
        key = pytilpack.base64.decode(key, url_safe=url_safe)
    plaintext_bytes = plaintext.encode("utf-8")
    nonce = secrets.token_bytes(12)
    cipher = Crypto.Cipher.AES.new(key, Crypto.Cipher.AES.MODE_GCM, nonce=nonce)
    ct, tag = cipher.encrypt_and_digest(plaintext_bytes)
    ciphertext = nonce + ct + tag
    ciphertext = pytilpack.base64.encode(ciphertext, url_safe=url_safe)
    return ciphertext


def decrypt(ciphertext: str, key: str | bytes, url_safe: bool = False) -> str:
    """復号。"""
    if isinstance(key, str):
        key = pytilpack.base64.decode(key, url_safe=url_safe)
    cipherbytes = pytilpack.base64.decode(ciphertext, url_safe=url_safe)
    nonce, ct, tag = cipherbytes[:12], cipherbytes[12:-16], cipherbytes[-16:]
    cipher = Crypto.Cipher.AES.new(key, Crypto.Cipher.AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ct, tag)
    return plaintext.decode("utf-8")
