"""pytilpack.base64_ のテスト。"""

import pytest

from pytilpack import base64_


@pytest.mark.parametrize(
    "input_data, expected_output",
    [
        ("hello", "aGVsbG8="),
        ("こんにちは", "44GT44KT44Gr44Gh44Gv"),
        (b"world", "d29ybGQ="),
        ("", ""),
    ],
)
def test_encode(input_data: str | bytes, expected_output: str) -> None:
    """encode関数のテスト。"""
    assert base64_.encode(input_data) == expected_output


@pytest.mark.parametrize(
    "input_data, expected_output",
    [
        ("aGVsbG8=", b"hello"),
        ("44GT44KT44Gr44Gh44Gv", "こんにちは".encode()),
        ("d29ybGQ=", b"world"),
        ("", b""),
    ],
)
def test_decode(input_data: str, expected_output: bytes) -> None:
    """decode関数のテスト。"""
    assert base64_.decode(input_data) == expected_output


def test_encode_decode_roundtrip() -> None:
    """エンコードとデコードのラウンドトリップテスト。"""
    original_str = "This is a test string with 日本語 characters."
    encoded = base64_.encode(original_str)
    decoded = base64_.decode(encoded)
    assert decoded == original_str.encode("utf-8")

    original_bytes = b"This is a test byte string \x01\x02\x03"
    encoded_bytes = base64_.encode(original_bytes)
    decoded_bytes = base64_.decode(encoded_bytes)
    assert decoded_bytes == original_bytes
