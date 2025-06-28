"""テストコード。"""

import typing

import pytest

import pytilpack.pycrypto


@pytest.mark.parametrize(
    "input_text,key_size",
    [
        ("Hello, World!", 32),
        ("日本語テスト", 16),
        ("", 32),
        ("a" * 1000, 24),
    ],
)
def test_encrypt_decrypt(input_text: str, key_size: int) -> None:
    """暗号化・復号化のテスト。"""
    key = pytilpack.pycrypto.create_key(key_size)
    ciphertext = pytilpack.pycrypto.encrypt(input_text, key)
    plaintext = pytilpack.pycrypto.decrypt(ciphertext, key)
    assert plaintext == input_text


@pytest.mark.parametrize(
    "obj",
    [
        {"name": "test", "value": 123},
        [1, 2, 3, "test"],
        "simple string",
        42,
        None,
        {"nested": {"data": ["a", "b", "c"]}, "日本語": "テスト"},
    ],
)
def test_encrypt_decrypt_json(obj: typing.Any) -> None:
    """JSON暗号化・復号化のテスト。"""
    key = pytilpack.pycrypto.create_key()
    ciphertext = pytilpack.pycrypto.encrypt_json(obj, key)
    plaintext = pytilpack.pycrypto.decrypt_json(ciphertext, key)
    assert plaintext == obj


def test_key_nonce_generation() -> None:
    """キー・nonce生成のテスト。"""
    # デフォルトサイズでのキー生成
    key1 = pytilpack.pycrypto.create_key()
    key2 = pytilpack.pycrypto.create_key()
    assert len(key1) == len(key2) == 44
    assert key1 != key2  # ランダムなので異なるはず

    # カスタムサイズでのキー生成
    key_16 = pytilpack.pycrypto.create_key(16)
    assert len(key_16) == 24


def test_decrypt_with_wrong_key() -> None:
    """間違ったキーでの復号化エラーのテスト。"""
    key1 = pytilpack.pycrypto.create_key()
    key2 = pytilpack.pycrypto.create_key()
    plaintext = "test data"

    ciphertext = pytilpack.pycrypto.encrypt(plaintext, key1)

    # 間違ったキーで復号化すると例外が発生するはず
    with pytest.raises((ValueError, UnicodeDecodeError)):
        pytilpack.pycrypto.decrypt(ciphertext, key2)


def test_fixed_ciphertext() -> None:
    """既知の暗号文の復号テスト。"""
    ciphertext = "Fp4zGMQ7ZL2a6krbjJRolhLFvNbE54lzRGRJXb0N4hFl1LIFNNRx+9Dg4mVSv6Q="
    key = "6rIA44107Qc3Fz9aSA2rccLvmddLlQ267G0zDnjr0Ss="
    plaintext = pytilpack.pycrypto.decrypt(ciphertext, key)
    assert plaintext == "日本語テスト!"
