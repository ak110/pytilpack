"""テストコード。"""

import dataclasses
import io

import pytest

import pytilpack.web

# HTML Standardのin body解析規則と名前空間規則から導いた公開入口共通の入力。
# https://html.spec.whatwg.org/multipage/parsing.html#parsing-main-inbody
HTML_VALID_CASES = [
    pytest.param("<select><option>日本語</option><hr><option>b</option></select>", id="select-hr"),
    pytest.param("<select><button><selectedcontent></selectedcontent></button><option>a</option></select>", id="select-button"),
    pytest.param("<select><option><span>a</span></option></select>", id="select-option-span"),
    pytest.param("<select><optgroup><legend>group</legend><option>a</option></optgroup></select>", id="select-legend"),
    pytest.param("<select><div><option>a</option><option>b</option></div></select>", id="select-div"),
    pytest.param(
        "<select><optgroup label='a'><option>a<option>b<hr><optgroup label='b'><option>c</select>", id="select-implied"
    ),
    pytest.param(
        "<select><optgroup label='a'><option>a</option><option>b</option></optgroup><hr>"
        "<optgroup label='b'><option>c</option></optgroup></select>",
        id="select-explicit",
    ),
    pytest.param("<table><tr><td><select><option>a<hr><option>b</select></td></tr></table>", id="table-select"),
    pytest.param("<select><option>a</option></select>", id="ordinary-select"),
    pytest.param("<select><template><option>a</option></template></select>", id="select-template"),
    pytest.param("<table><tbody><template><tr><td>a</td></tr></template></tbody></table>", id="table-template"),
    pytest.param("<svg><circle r='1'/></svg><math><mi>x</mi></math><search><dialog open>x</dialog></search>", id="controls"),
    pytest.param("<template><template><tr><td>x</td></tr></template></template>", id="nested-template"),
    pytest.param("<svg><script/><template/></svg><template><tr><td>x</td></tr></template>", id="svg-self-closing"),
    pytest.param("<svg><![CDATA[<template>]]></svg><template><tr><td>x</td></tr></template>", id="svg-cdata"),
    pytest.param("<svg><foreignObject><template><tr><td>x</td></tr></template></foreignObject></svg>", id="svg-integration"),
    pytest.param(
        "<math><annotation-xml encoding='text/html'><template><tr><td>x</td></tr></template></annotation-xml></math>",
        id="math-integration",
    ),
    pytest.param("<math><mtext><template><tr><td>x</td></tr></template></mtext></math>", id="math-text-integration"),
    *[
        pytest.param(f"<{tag}>text &lt;template&gt;</{tag}><template><tr><td>x</td></tr></template>", id=f"text-{tag}")
        for tag in ("script", "style", "xmp", "iframe", "noembed", "noframes", "title", "textarea")
    ],
]

HTML_INVALID_CASES = [
    pytest.param("<select><option>a</div></option></select>", ("div",), id="select-end-tag"),
    pytest.param("<select><input></select>", ("input",), id="select-input"),
    pytest.param("<select><select></select>", ("select",), id="nested-select"),
    pytest.param("<select><option>a", ("end of file",), id="unclosed-select"),
    pytest.param("<select id='a' id='b'></select>", ("duplicate attribute",), id="duplicate-attribute"),
    pytest.param("<select></select><p>a</div>", ("div",), id="outside-select"),
    pytest.param("<select><option><span>a<option>b</select>", ("option",), id="option-scope"),
    pytest.param("<select><optgroup><div><optgroup></select>", ("optgroup",), id="optgroup-scope"),
    pytest.param("<select><option><span>a<hr></select>", ("hr",), id="hr-scope"),
    pytest.param("<select><div></select>", ("select",), id="select-close-scope"),
    *[
        pytest.param(
            f'<template><{tag}{solidus}>var s="<template>";</{tag}></template><p>a</div></template>',
            ("div", "template"),
            id=f"boundary-{tag}-{'solidus' if solidus else 'normal'}",
        )
        for tag in ("script", "style", "xmp", "iframe", "noembed", "noframes", "title", "textarea")
        for solidus in ("", "/")
    ],
    pytest.param("<template><plaintext>text</template><p>a</div></template>", ("end of file",), id="plaintext"),
    pytest.param("<svg><template><p>a</div></template></svg>", ("div",), id="foreign-template"),
    pytest.param("<math><template><p>a</div></template></math>", ("div",), id="math-template"),
    pytest.param("<svg><script/><template/><p>a</div>", ("div",), id="foreign-self-closing"),
    pytest.param("<svg><![CDATA[<template>]]><p>a</div></template>", ("div",), id="cdata-outside"),
    pytest.param(
        "<svg><foreignObject><template>x</template><p>a</div></template></foreignObject></svg>",
        ("div", "template"),
        id="integration-outside",
    ),
    pytest.param("<template><template>x</template></template><p>a</div>", ("div",), id="nested-outside"),
    pytest.param("<template><p>a</div>", ("div",), id="unclosed-template"),
    pytest.param("<frameset><script><template></script></frameset></template>", ("script",), id="ignored-script"),
    pytest.param("<svg><script><template/></script></svg><p>a</div></template>", ("div",), id="svg-script"),
]


@pytest.mark.parametrize("fragment", HTML_VALID_CASES)
@pytest.mark.parametrize("input_kind", ["str", "bytes", "text-file", "binary-file"])
def test_check_html_current_syntax(fragment: str, input_kind: str, caplog: pytest.LogCaptureFixture) -> None:
    """現行select・template・名前空間の正例を各入力型と両strict値で検査する。"""
    html = f"<!doctype html><meta charset='utf-8'><title>t</title>\n{fragment}"
    for strict in (True, False):
        value = {"str": html, "bytes": html.encode(), "text-file": io.StringIO(html), "binary-file": io.BytesIO(html.encode())}
        pytilpack.web.check_html(value[input_kind], strict=strict)
    assert not [record for record in caplog.records if record.name == "pytilpack.web" and "HTMLエラー:" in record.message]


@pytest.mark.parametrize("fragment,expected", HTML_INVALID_CASES)
def test_check_html_diagnostics_retained(fragment: str, expected: tuple[str, ...], caplog: pytest.LogCaptureFixture) -> None:
    """selectの不正構文と本パーサーのtemplate境界外の診断を保持する。"""
    html = f"<!doctype html><meta charset='utf-8'><title>t</title>\n{fragment}"
    with pytest.raises(AssertionError) as exc_info:
        pytilpack.web.check_html(html, strict=True)
    pytilpack.web.check_html(html.encode(), strict=False)
    for diagnostic in expected:
        assert diagnostic in str(exc_info.value).lower()
        assert diagnostic in caplog.text.lower()


@pytest.mark.parametrize("file_like", [False, True])
def test_check_html_reparsed_bytes(file_like: bool, caplog: pytest.LogCaptureFixture) -> None:
    """先読み範囲より後のcharset宣言による再解析でもtemplate境界を初期化する。"""
    # charsetの先読み（1024 bytes）の外で、未終了のtemplateを持つ解析をやり直す。
    html = "<!doctype html><title>t</title><!--" + "x" * 1024 + "-->"
    html += "<template><meta charset='utf-8'><tr><td>日本語</td></tr></template>"
    for strict in (True, False):
        data = html.encode()
        pytilpack.web.check_html(io.BytesIO(data) if file_like else data, strict=strict)
    assert "HTMLエラー:" not in caplog.text
    with pytest.raises(AssertionError, match="div"):
        data = (html + "<p>a</div>").encode()
        pytilpack.web.check_html(io.BytesIO(data) if file_like else data, strict=True)


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


@pytest.mark.parametrize(
    "html",
    [
        # select内のtemplate
        '<!DOCTYPE html><title>t</title><select><template x-for="o in options"><option>x</option></template></select>',
        # 表の中のtemplate
        '<!DOCTYPE html><title>t</title><table><tbody><template x-for="r in rows">'
        "<tr><td>x</td></tr></template></tbody></table>",
        # div内のtemplateが行を内容に持つ（templateタグ自体へのエラーは出ない）
        "<!DOCTYPE html><title>t</title><div><template><tr><td>x</td></tr></template></div>",
        # 複数行・入れ子のtemplate（bytes入力）
        b"<!DOCTYPE html><title>t</title>\n<table>\n<template x-if='a'>\n"
        b"<template x-for='r in rows'><tr><td>x</td></tr></template>\n</template>\n</table>",
    ],
)
def test_check_html_template_ok(html: str | bytes, caplog: pytest.LogCaptureFixture) -> None:
    """template要素を含む正しいHTMLでエラーを報告しないことの確認。

    html5lib 1.1はtemplate要素の構文規則を持たず、正しいHTMLにもエラーを記録するため。
    """
    pytilpack.web.check_html(html, strict=True)
    pytilpack.web.check_html(html, strict=False)
    assert "HTMLエラー:" not in caplog.text


@pytest.mark.parametrize(
    "html",
    [
        # templateを含まない誤り
        "<!DOCTYPE html><title>t</title><table><tr>bad</div></table>",
        # templateの後ろの誤り
        "<!DOCTYPE html><title>t</title><template><b>x</b></template><p>a</div>",
        # script内の文字列<template>はtemplate要素として扱わない（後続の終了タグと組にしない）
        '<!DOCTYPE html><title>t</title><script>var s = "<template>";</script><p>a</div></template>',
        # 終了タグの無いtemplateは除外の対象にしない
        "<!DOCTYPE html><title>t</title><p>a</div><template>",
    ],
)
def test_check_html_template_outside_error(html: str) -> None:
    """template要素の範囲外にある誤りを引き続き報告することの確認。"""
    with pytest.raises(AssertionError) as exc_info:
        pytilpack.web.check_html(html, strict=True)
    assert "HTMLエラー:" in str(exc_info.value)


def test_check_html_file_like_template_ok() -> None:
    """ファイル風オブジェクトの入力でもtemplate範囲のエラーを報告しないことの確認。"""
    html = b"<!DOCTYPE html><title>t</title><select><template><option>x</option></template></select>"
    pytilpack.web.check_html(io.BytesIO(html), strict=True)


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
