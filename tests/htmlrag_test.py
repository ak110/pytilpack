import httpx
import pytest

import pytilpack.functools
import pytilpack.htmlrag


def test_htmlrag_clean():
    html = """
<html>
<head>
<h1>Bellagio Hotel in Las</h1>
</head>
<body>
<p class="class0">The Bellagio is a luxury hotel and casino located
 on the Las Vegas Strip in Paradise, Nevada. It was built in 1998.</p>
</body>
<div>
<div>
<p>Some other text</p>
<p>Some other text</p>
</div>
</div>
<p class="class1"></p>
<!-- Some comment -->
<script type="text/javascript">
document.write("Hello World!");
</script>
</html>
"""
    simplified_html = pytilpack.htmlrag.clean_html(html, aggressive=False, keep_title=True, keep_href=False)
    assert (
        simplified_html
        == """<html>
<h1>Bellagio Hotel in Las</h1>
<p>The Bellagio is a luxury hotel and casino located
 on the Las Vegas Strip in Paradise, Nevada. It was built in 1998.</p>
<div>
<p>Some other text</p>
<p>Some other text</p>
</div>
</html>"""
    )


def test_htmlrag_clean_aggressive():
    html = """
<html>
<head>
<title>タイトル</title>
</head>
<body>
<nav>めにゅー</nav>
<h1>見出し</h1>
<div>
<div>
<p>Some other text</p>
<p><a href="./a.txt">link to a.txt</a></p>
<aside>関連記事！</aside>
</div>
</div>
</body>
</html>
"""
    simplified_html = pytilpack.htmlrag.clean_html(html, aggressive=True, keep_title=False, keep_href=True)
    assert (
        simplified_html
        == """<h1>見出し</h1>
<p>Some other text</p>
<a href="./a.txt">link to a.txt</a>"""
    )


def test_htmlrag_clean_bytes():
    html = """<html><meta charset="Shift_JIS">バイナリデータ</html>""".encode("cp932")
    simplified_html = pytilpack.htmlrag.clean_html(html, aggressive=True)
    assert simplified_html == "バイナリデータ"


@pytest.fixture(name="stub_response")
def _stub_response(monkeypatch: pytest.MonkeyPatch):
    def stub(status: int, content_type: str | None, text: str) -> None:
        headers = {} if content_type is None else {"Content-Type": content_type}
        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(status, headers=headers, content=text.encode(), request=request)
        monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: response)

    return stub


@pytest.mark.parametrize("content_type", [None, "text/html; charset=utf-8"])
def test_fetch_url_html(stub_response, content_type: str | None) -> None:
    html = "<html><head><title>T</title></head><body><header>H</header><p>本文</p></body></html>"
    stub_response(200, content_type, html)
    assert pytilpack.htmlrag.fetch_url("https://example.com") == "<title>T</title><p>本文</p>"


@pytest.mark.parametrize(
    "content_type",
    ["text/markdown", "text/plain; charset=utf-8", "text/csv", "text/xml", "application/xml", "application/json"],
)
def test_fetch_url_passthrough(stub_response, content_type: str) -> None:
    text = "<header>raw</header><p>body</p>"
    stub_response(200, content_type, text)
    assert pytilpack.htmlrag.fetch_url("https://example.com") == text


def test_fetch_url_raw(stub_response) -> None:
    html = "<html><body><header>H</header><p>本文</p></body></html>"
    stub_response(200, "text/html", html)
    assert pytilpack.htmlrag.fetch_url("https://example.com", raw=True) == html


def test_fetch_url_unsupported_type(stub_response) -> None:
    stub_response(200, "image/png", "xxx")
    with pytest.raises(RuntimeError, match="Content-Type: image/png"):
        pytilpack.htmlrag.fetch_url("https://example.com")


def test_fetch_url_status_error(stub_response) -> None:
    stub_response(404, "text/html", "not found")
    with pytest.raises(RuntimeError, match="Status: 404"):
        pytilpack.htmlrag.fetch_url("https://example.com")


def test_fetch_url_retry(monkeypatch: pytest.MonkeyPatch):
    request = httpx.Request("GET", "https://example.com")
    responses = [
        httpx.Response(503, request=request),
        httpx.Response(200, headers={"Content-Type": "text/plain"}, text="ok", request=request),
    ]
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: responses.pop(0))
    monkeypatch.setattr(pytilpack.functools.time, "sleep", lambda seconds: None)
    assert pytilpack.htmlrag.fetch_url("https://example.com") == "ok"
