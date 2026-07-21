"""テストコード。"""

import dataclasses

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
def test_get_safe_url(target: str | None, host_url: str, default_url: str, expected: str) -> None:
    """get_safe_urlのテスト。"""
    actual = pytilpack.web.get_safe_url(target, host_url, default_url)
    assert actual == expected


def test_check_status_code_ok() -> None:
    """check_status_codeの正常系のテスト（一致時に例外が発生しないことの確認）。"""
    pytilpack.web.check_status_code(200, 200)


def test_check_status_code_error() -> None:
    """check_status_codeの異常系のテスト（不一致時にAssertionErrorが送出されることの確認）。"""
    with pytest.raises(AssertionError) as exc_info:
        pytilpack.web.check_status_code(404, 200)
    assert "ステータスコードエラー: 404 != 200" in str(exc_info.value)


@pytest.mark.parametrize(
    "content_type,valid_types",
    [
        # valid_types=None
        ("text/html", None),
        # valid_typesが文字列
        ("text/html", "text/html"),
        # valid_typesが配列
        ("text/html", ["text/html", "application/json"]),
        # Content-Typeにパラメータがある場合
        ("text/html; charset=utf-8", "text/html"),
    ],
)
def test_check_content_type_ok(content_type: str, valid_types: str | list[str] | None) -> None:
    """check_content_typeの正常系のテスト（一致時に例外が発生しないことの確認）。"""
    pytilpack.web.check_content_type(content_type, valid_types)


def test_check_content_type_error() -> None:
    """check_content_typeの異常系のテスト（不一致時にAssertionErrorが送出されることの確認）。"""
    with pytest.raises(AssertionError) as exc_info:
        pytilpack.web.check_content_type("text/plain", "text/html")
    assert "Content-Typeエラー: text/plain != ['text/html']" in str(exc_info.value)


@pytest.mark.parametrize(
    "html",
    [
        # 正常系
        "<html><body><h1>Hello</h1></body></html>",
        # 空HTML
        "",
    ],
)
def test_check_html_ok(html: str) -> None:
    """check_htmlの正常系のテスト（構文エラーが無い場合に例外が発生しないことの確認）。"""
    pytilpack.web.check_html(html, strict=False)


def test_check_html_strict_error() -> None:
    """check_htmlのstrict=True時の異常系のテスト（構文エラー時にAssertionErrorが送出されることの確認）。"""
    with pytest.raises(AssertionError) as exc_info:
        pytilpack.web.check_html("<table><tr>Invalid table structure</div>", strict=True)
    assert "HTMLエラー:" in str(exc_info.value)


def test_check_html_non_strict_error(caplog: pytest.LogCaptureFixture) -> None:
    """check_htmlのstrict=False時の異常系のテスト（構文エラー時に例外を送出せずログ出力することの確認）。"""
    pytilpack.web.check_html("<table><tr>Invalid table structure</div>", strict=False)
    assert "HTMLエラー:" in caplog.text


@pytest.mark.parametrize(
    "value,expected",
    [
        # 正常系
        ("/app", "/app"),
        ("/app/sub", "/app/sub"),
        ("/app/", "/app"),  # 末尾スラッシュは除去
        ("/app//sub", "/app//sub"),  # パス内の//はOK（先頭の//のみ拒否）
        # 末尾スラッシュを複数持つケース
        ("/app///", "/app"),
        # 許可文字全種
        ("/a-b_c.d~e:f@g!h$i&j'k(l)m*n+o,p;q=r%20", "/a-b_c.d~e:f@g!h$i&j'k(l)m*n+o,p;q=r%20"),
        # 異常系: 空文字
        ("", None),
        # 異常系: 先頭が/でない
        ("app", None),
        ("//evil.com", None),  # プロトコル相対形式
        # 異常系: /単独（正規化後に空になる）
        ("/", None),
        ("///", None),
        # 異常系: 制御文字
        ("/app\r\nX-Inject: evil", None),
        ("/app\x00", None),
        ("/app\x0a", None),
        # 異常系: 許可文字集合外（スペース・日本語など）
        ("/app path", None),
        ("/アプリ", None),
        ("/app?query=1", None),  # query文字列はNG
        ("/app#frag", None),  # fragmentはNG
    ],
)
def test_validate_forwarded_prefix(value: str, expected: str | None) -> None:
    """validate_forwarded_prefixのテスト。"""
    assert pytilpack.web.validate_forwarded_prefix(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        # 正常系
        ("example.com", "example.com"),
        ("example.com:8080", "example.com:8080"),
        ("[::1]", "[::1]"),
        ("[::1]:8080", "[::1]:8080"),
        ("192.168.1.1", "192.168.1.1"),
        ("192.168.1.1:443", "192.168.1.1:443"),
        # 異常系: 空文字
        ("", None),
        # 異常系: //で始まる
        ("//evil.com", None),
        # 異常系: 制御文字（CRLF）
        ("evil.com\r\nX-Inject: bad", None),
        ("evil.com\n", None),
        ("evil.com\x00", None),
        # 異常系: 空白を含む
        ("evil .com", None),
        ("evil\tcom", None),
        # 異常系: [で始まるが]を含まない不完全なIPv6形式
        ("[::1", None),
        ("[", None),
    ],
)
def test_validate_forwarded_host(value: str, expected: str | None) -> None:
    """validate_forwarded_hostのテスト。"""
    assert pytilpack.web.validate_forwarded_host(value) == expected


@pytest.mark.parametrize(
    "host_value,trusted_hosts,expected",
    [
        # 正常系: ホスト名のみ
        ("example.com", ["example.com"], True),
        ("example.com", ["other.com", "example.com"], True),
        ("example.com", ["other.com"], False),
        # ポート付きホスト（ポートは無視）
        ("example.com:8080", ["example.com"], True),
        ("example.com:8080", ["other.com"], False),
        # IPv6アドレス（[]内のアドレスで照合）
        ("[::1]:8080", ["::1"], True),
        ("[::1]:8080", ["other"], False),
        ("[::1]", ["::1"], True),
        # ポートなし
        ("192.168.1.1", ["192.168.1.1"], True),
        ("192.168.1.1", ["192.168.1.2"], False),
    ],
)
def test_is_host_in_trusted(host_value: str, trusted_hosts: list[str], expected: bool) -> None:
    """is_host_in_trustedのテスト。"""
    assert pytilpack.web.is_host_in_trusted(host_value, trusted_hosts) == expected


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


@dataclasses.dataclass
class _PrefixPinnerFixture:
    """PrefixPinnerテスト用の共通セットアップ結果。"""

    applied: list[str]
    warned: list[str]
    pinner: pytilpack.web.PrefixPinner


@pytest.fixture(name="prefix_pinner_fixture")
def _prefix_pinner_fixture() -> _PrefixPinnerFixture:
    """applied・warnedの記録リストとPrefixPinnerインスタンスを組み立てる。"""
    applied: list[str] = []
    warned: list[str] = []
    pinner = pytilpack.web.PrefixPinner(apply=applied.append, warn=warned.append)
    return _PrefixPinnerFixture(applied=applied, warned=warned, pinner=pinner)


def test_prefix_pinner_initialize_applies_static_prefix(prefix_pinner_fixture: _PrefixPinnerFixture) -> None:
    """initializeでstatic_prefixが検証・適用され、以降のpinで固定されることのテスト。"""
    applied, warned, pinner = prefix_pinner_fixture.applied, prefix_pinner_fixture.warned, prefix_pinner_fixture.pinner
    pinner.initialize("/static")
    assert applied == ["/static"]
    assert not warned
    # initialize後はpin済み扱いのため、pinへ異なる値を渡すと警告が発火する
    pinner.pin("/other")
    assert applied == ["/static"]
    assert len(warned) == 1
    assert "/static" in warned[0]
    assert "/other" in warned[0]


def test_prefix_pinner_initialize_invalid_static_prefix_raises(prefix_pinner_fixture: _PrefixPinnerFixture) -> None:
    """initializeで不正なstatic_prefixを渡すとValueErrorが送出されることのテスト。"""
    applied, warned, pinner = prefix_pinner_fixture.applied, prefix_pinner_fixture.warned, prefix_pinner_fixture.pinner
    with pytest.raises(ValueError, match="static_prefixが不正"):
        pinner.initialize("invalid")
    assert not applied
    assert not warned


def test_prefix_pinner_initialize_none_is_noop(prefix_pinner_fixture: _PrefixPinnerFixture) -> None:
    """initializeでstatic_prefix=Noneを渡すとapply・warnのいずれも呼ばれないことのテスト。"""
    applied, warned, pinner = prefix_pinner_fixture.applied, prefix_pinner_fixture.warned, prefix_pinner_fixture.pinner
    pinner.initialize(None)
    assert not applied
    assert not warned


def test_prefix_pinner_pin_first_call_fixes_value(prefix_pinner_fixture: _PrefixPinnerFixture) -> None:
    """pinの初回呼び出しで値が確定し、applyへ反映されることのテスト。"""
    applied, warned, pinner = prefix_pinner_fixture.applied, prefix_pinner_fixture.warned, prefix_pinner_fixture.pinner
    pinner.pin("/app")
    assert applied == ["/app"]
    assert not warned


def test_prefix_pinner_pin_second_call_same_value_no_warn(prefix_pinner_fixture: _PrefixPinnerFixture) -> None:
    """pinの2回目以降で同一値なら値が固定されたまま警告が発火しないことのテスト。"""
    applied, warned, pinner = prefix_pinner_fixture.applied, prefix_pinner_fixture.warned, prefix_pinner_fixture.pinner
    pinner.pin("/app")
    pinner.pin("/app")
    assert applied == ["/app"]  # applyは初回のみ呼ばれる
    assert not warned


def test_prefix_pinner_pin_second_call_different_value_warns(prefix_pinner_fixture: _PrefixPinnerFixture) -> None:
    """pinの2回目以降で異なる値が渡された場合に警告コールバックが発火することのテスト。"""
    applied, warned, pinner = prefix_pinner_fixture.applied, prefix_pinner_fixture.warned, prefix_pinner_fixture.pinner
    pinner.pin("/app")
    pinner.pin("/other")
    assert applied == ["/app"]  # applyは初回のみ呼ばれる
    assert len(warned) == 1
    assert "/app" in warned[0]
    assert "/other" in warned[0]
