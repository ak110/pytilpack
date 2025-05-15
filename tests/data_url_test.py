"""テストコード。"""

import pytilpack.data_url


def test_create() -> None:
    assert (
        pytilpack.data_url.create("text/plain", b"Hello, World!")
        == "data:text/plain;base64,SGVsbG8sIFdvcmxkIQ=="
    )


def test_parse_plain() -> None:
    assert pytilpack.data_url.parse(
        "data:,Hello%2C%20World%21"
    ) == pytilpack.data_url.DataURL(
        mime_type="text/plain", encoding="plain", data=b"Hello, World!"
    )


def test_parse_base64() -> None:
    assert pytilpack.data_url.parse(
        "data:text/plain;base64,SGVsbG8sIFdvcmxkIQ=="
    ) == pytilpack.data_url.DataURL(
        mime_type="text/plain", encoding="base64", data=b"Hello, World!"
    )
