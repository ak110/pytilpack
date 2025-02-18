"""テストコード。

<https://github.com/plageon/HtmlRAG/blob/main/toolkit/README.md>

"""

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
    simplified_html = pytilpack.htmlrag.clean_html(
        html, aggressive=False, keep_title=True, keep_href=False
    )
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
    simplified_html = pytilpack.htmlrag.clean_html(
        html, aggressive=True, keep_title=False, keep_href=True
    )
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
