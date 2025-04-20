"""テストコード。"""

import pytest

import pytilpack.web


@pytest.mark.parametrize(
    "target,host_url,default_url,expected",
    [
        # targetが空の場合はdefault_urlを返す
        ("", "http://example.com", "/home", "/home"),
        # targetがNoneの場合はdefault_urlを返す
        (None, "http://example.com", "/home", "/home"),
        # 無効なスキームの場合はdefault_urlを返す
        ("ftp://example.com/path", "http://example.com", "/home", "/home"),
        # 異なるホストの場合はdefault_urlを返す
        ("http://evil.com/path", "http://example.com", "/home", "/home"),
        # 異なるホストの場合はdefault_urlを返す（https）
        ("https://evil.com/path", "https://example.com", "/home", "/home"),
        # 正常なパスの場合はtargetを返す（相対パス）
        ("/path", "http://example.com", "/home", "/path"),
        # 正常なパスの場合はtargetを返す（絶対パス）
        (
            "http://example.com/path",
            "http://example.com",
            "/home",
            "http://example.com/path",
        ),
        # 正常なパスの場合はtargetを返す（https）
        (
            "https://example.com/path",
            "https://example.com",
            "/home",
            "https://example.com/path",
        ),
    ],
)
def test_get_safe_url(
    target: str | None, host_url: str, default_url: str, expected: str
) -> None:
    """get_safe_urlのテスト。"""
    actual = pytilpack.web.get_safe_url(target, host_url, default_url)
    assert actual == expected
