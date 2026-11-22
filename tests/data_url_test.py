import pytest

import pytilpack.data_url


def test_data_url() -> None:
    assert pytilpack.data_url.create("text/plain", b"Hello, World!") == "data:text/plain;base64,SGVsbG8sIFdvcmxkIQ=="

    assert pytilpack.data_url.DataURL(data=b"Hello, World!", encoding="plain").to_url() == "data:,Hello%2C%20World%21"
    assert pytilpack.data_url.DataURL(data=b"Hello, World!").to_url() == "data:;base64,SGVsbG8sIFdvcmxkIQ=="

    assert pytilpack.data_url.parse("data:,Hello%2C%20World%21") == pytilpack.data_url.DataURL(
        mime_type="text/plain", encoding="plain", data=b"Hello, World!"
    )
    assert pytilpack.data_url.parse("data:text/plain;base64,SGVsbG8sIFdvcmxkIQ==") == pytilpack.data_url.DataURL(
        mime_type="text/plain", encoding="base64", data=b"Hello, World!"
    )

    assert pytilpack.data_url.get_base64_data("data:,Hello%2C%20World%21") == "SGVsbG8sIFdvcmxkIQ=="
    assert pytilpack.data_url.get_base64_data("data:text/plain;base64,SGVsbG8sIFdvcmxkIQ==") == "SGVsbG8sIFdvcmxkIQ=="


@pytest.mark.parametrize("url", ["http://example.com/,hello", "data:text/plain"])
def test_parse_invalid(url: str) -> None:
    with pytest.raises(ValueError):
        pytilpack.data_url.parse(url)
