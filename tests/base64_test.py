"""pytilpack.base64 のテスト。"""

import pytest

import pytilpack.base64


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
    assert pytilpack.base64.encode(input_data) == expected_output


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
    assert pytilpack.base64.decode(input_data) == expected_output


def test_encode_decode_roundtrip() -> None:
    """エンコードとデコードのラウンドトリップテスト。"""
    original_str = "This is a test string with 日本語 characters."
    encoded = pytilpack.base64.encode(original_str)
    decoded = pytilpack.base64.decode(encoded)
    assert decoded == original_str.encode("utf-8")

    original_bytes = b"This is a test byte string \x01\x02\x03"
    encoded_bytes = pytilpack.base64.encode(original_bytes)
    decoded_bytes = pytilpack.base64.decode(encoded_bytes)
    assert decoded_bytes == original_bytes
