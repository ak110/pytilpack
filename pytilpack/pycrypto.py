__lazy_modules__ = ["Crypto.Cipher.AES", "json", "pytilpack.base64", "secrets", "typing"]

import json
import secrets
import typing

import Crypto.Cipher.AES

import pytilpack.base64

DEFAULT_KEY_SIZE = 32


def create_key(nbytes: int = DEFAULT_KEY_SIZE, url_safe: bool = False) -> str:
    return pytilpack.base64.encode(secrets.token_bytes(nbytes), url_safe=url_safe)


def encrypt_json(obj: typing.Any, key: str | bytes, url_safe: bool = False) -> str:
    return encrypt(json.dumps(obj), key, url_safe=url_safe)


def decrypt_json(s: str, key: str | bytes, url_safe: bool = False) -> typing.Any:
    return json.loads(decrypt(s, key, url_safe=url_safe))


def encrypt(plaintext: str, key: str | bytes, url_safe: bool = False) -> str:
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
    if isinstance(key, str):
        key = pytilpack.base64.decode(key, url_safe=url_safe)
    cipherbytes = pytilpack.base64.decode(ciphertext, url_safe=url_safe)
    nonce, ct, tag = cipherbytes[:12], cipherbytes[12:-16], cipherbytes[-16:]
    cipher = Crypto.Cipher.AES.new(key, Crypto.Cipher.AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ct, tag)
    return plaintext.decode("utf-8")
