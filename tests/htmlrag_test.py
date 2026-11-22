"""テストコード。

<https://github.com/plageon/HtmlRAG/blob/main/toolkit/README.md>

"""

# pylint: disable=protected-access

import pytest

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


@pytest.mark.parametrize("content_type", [None, "text/html; charset=utf-8"])
def test_process_fetched_response_html(content_type: str | None):
    html = "<html><head><title>T</title></head><body><header>H</header><p>本文</p></body></html>"
    expected = pytilpack.htmlrag.clean_html(html, aggressive=True, keep_title=True, keep_href=True)
    actual = pytilpack.htmlrag._process_fetched_response("https://example.com", 200, content_type, html)
    assert actual == expected


@pytest.mark.parametrize(
    "content_type", ["text/markdown", "text/plain; charset=utf-8", "text/xml", "application/xml", "application/json"]
)
def test_process_fetched_response_passthrough(content_type: str):
    text = "<p>raw</p>"
    assert pytilpack.htmlrag._process_fetched_response("https://example.com", 200, content_type, text) == text


def test_process_fetched_response_not_html():
    with pytest.raises(RuntimeError, match="HTMLではありません"):
        pytilpack.htmlrag._process_fetched_response("https://example.com", 200, "image/png", "xxx")


def test_process_fetched_response_status_error():
    with pytest.raises(RuntimeError, match="Status: 404"):
        pytilpack.htmlrag._process_fetched_response("https://example.com", 404, "text/html", "not found")
