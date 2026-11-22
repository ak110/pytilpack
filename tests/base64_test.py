import pytest

import pytilpack.base64


@pytest.mark.parametrize(
    "input_data, expected_output",
    [
        ("hello", "aGVsbG8="),
        ("こんにちは", "44GT44KT44Gr44Gh44Gv"),
        (b"world", "d29ybGQ="),
        ("This is a test string with 日本語 characters.", "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIHdpdGgg5pel5pys6KqeIGNoYXJhY3RlcnMu"),
        (b"This is a test byte string \x01\x02\x03", "VGhpcyBpcyBhIHRlc3QgYnl0ZSBzdHJpbmcgAQID"),
        ("", ""),
    ],
)
def test_encode(input_data: str | bytes, expected_output: str) -> None:
    assert pytilpack.base64.encode(input_data) == expected_output


@pytest.mark.parametrize(
    "input_data, expected_output",
    [
        ("aGVsbG8=", b"hello"),
        ("44GT44KT44Gr44Gh44Gv", "こんにちは".encode()),
        ("d29ybGQ=", b"world"),
        (
            "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIHdpdGgg5pel5pys6KqeIGNoYXJhY3RlcnMu",
            "This is a test string with 日本語 characters.".encode(),
        ),
        ("VGhpcyBpcyBhIHRlc3QgYnl0ZSBzdHJpbmcgAQID", b"This is a test byte string \x01\x02\x03"),
        ("", b""),
    ],
)
def test_decode(input_data: str, expected_output: bytes) -> None:
    assert pytilpack.base64.decode(input_data) == expected_output
