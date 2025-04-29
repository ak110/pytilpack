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


@pytest.mark.parametrize(
    "status_code,valid_status_code,expected_error",
    [
        # 正常系
        (200, 200, None),
        # 異常系
        (404, 200, "ステータスコードエラー: 404 != 200"),
    ],
)
def test_check_status_code(
    status_code: int, valid_status_code: int, expected_error: str | None
) -> None:
    """check_status_codeのテスト。"""
    if expected_error is None:
        pytilpack.web.check_status_code(
            status_code, valid_status_code
        )  # 例外が発生しないことを確認
    else:
        with pytest.raises(AssertionError) as exc_info:
            pytilpack.web.check_status_code(status_code, valid_status_code)
        assert expected_error in str(exc_info.value)


@pytest.mark.parametrize(
    "content_type,valid_types,expected_error",
    [
        # valid_types=None
        ("text/html", None, None),
        # valid_typesが文字列
        ("text/html", "text/html", None),
        # valid_typesが配列
        ("text/html", ["text/html", "application/json"], None),
        # Content-Typeにパラメータがある場合
        ("text/html; charset=utf-8", "text/html", None),
        # 異常系
        ("text/plain", "text/html", "Content-Typeエラー: text/plain != ['text/html']"),
    ],
)
def test_check_content_type(
    content_type: str, valid_types: str | list[str] | None, expected_error: str | None
) -> None:
    """check_content_typeのテスト。"""
    if expected_error is None:
        pytilpack.web.check_content_type(
            content_type, valid_types
        )  # 例外が発生しないことを確認
    else:
        with pytest.raises(AssertionError) as exc_info:
            pytilpack.web.check_content_type(content_type, valid_types)
        assert expected_error in str(exc_info.value)


@pytest.mark.parametrize(
    "html,strict,expected_error",
    [
        # 正常系
        ("<html><body><h1>Hello</h1></body></html>", False, None),
        # 空HTML
        ("", False, None),
        # 誤った閉じタグ（strict=False）
        ("<table><tr>Invalid table structure</div>", False, "HTMLエラー:"),
        # 誤った閉じタグ（strict=True）
        ("<table><tr>Invalid table structure</div>", True, "HTMLエラー:"),
    ],
)
def test_check_html(
    html: str,
    strict: bool,
    expected_error: str | None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """check_htmlのテスト。"""
    if expected_error is None:
        pytilpack.web.check_html(html, strict)  # 例外が発生しないことを確認
    elif strict:
        with pytest.raises(AssertionError) as exc_info:
            pytilpack.web.check_html(html, strict)
        assert expected_error in str(exc_info.value)
    else:
        pytilpack.web.check_html(html, strict)
        assert expected_error in caplog.text


def test_check_html_complex_error(caplog: pytest.LogCaptureFixture) -> None:
    """check_htmlの複雑なHTML構文エラーのテスト。"""
    html = """
    <!DOCTYPE html>
    <html>
        <body>
            <table>
                <th>Missing tr tag</th>
                <tr><td>Cell</tr>  <!-- tdタグが閉じられていない -->
            </table>
            <div>Unclosed div
            <p>Wrong nesting</div></p>  <!-- ネストが間違っている -->
        </body>
    </html>
    """
    pytilpack.web.check_html(html, strict=False)
    assert "HTMLエラー:" in caplog.text
    assert len([r for r in caplog.records if "HTMLエラー:" in r.message]) > 1
