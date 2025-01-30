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
    simplified_html = pytilpack.htmlrag.clean_html(html)
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
