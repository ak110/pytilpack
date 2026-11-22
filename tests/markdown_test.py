import pytilpack.markdown


def test_markdownfy_basic():
    text = "# Hello\n\nThis is a test."
    result = pytilpack.markdown.markdownfy(text)
    assert ">Hello</h1>" in result
    assert "<p>This is a test.</p>" in result

    assert pytilpack.markdown.markdownfy("") == ""

    text = """```
    def hello():
        print("Hello")
    ```"""
    result = pytilpack.markdown.markdownfy(text)
    assert "<code>" in result

    text = """| Left | Right | Center |
|:----|----:|:----:|
| 1 | 2 | 3 |"""
    result = pytilpack.markdown.markdownfy(text)
    assert "<table>" in result
    assert '<th style="text-align: left;">' in result
    assert '<th style="text-align: right;">' in result
    assert '<th style="text-align: center;">' in result
    assert '<td style="text-align: left;">' in result
    assert '<td style="text-align: right;">' in result
    assert '<td style="text-align: center;">' in result


def test_markdownfy_with_html_tag():
    html = "<script>alert('test')</script>"
    result = pytilpack.markdown.markdownfy(html)
    assert "<script>" not in result
    assert "&lt;script&gt;" in result

    html = "<details><summary>サマリ</summary>詳細</details>"
    result = pytilpack.markdown.markdownfy(html)
    assert html in result

    html = "<think>最近流行りのreasoning</think>結果"
    result = pytilpack.markdown.markdownfy(html)
    assert "<think>" not in result
    assert "&lt;think&gt;" in result


def test_markdownfy_with_malicious_content():
    text = "[click me](javascript:alert('test'))"
    result = pytilpack.markdown.markdownfy(text)
    assert "javascript:" not in result


def test_escape() -> None:
    assert pytilpack.markdown.escape("Hello *world*") == r"Hello \*world\*"
    assert pytilpack.markdown.escape("a\\b") == r"a\\b"
    assert pytilpack.markdown.escape("[link](url)") == r"\[link\]\(url\)"


def test_inline_code() -> None:
    assert pytilpack.markdown.inline_code("foo") == "`foo`"
    assert pytilpack.markdown.inline_code("foo`bar") == "``foo`bar``"
    assert pytilpack.markdown.inline_code("`foo") == "`` `foo ``"
    assert pytilpack.markdown.inline_code("foo`") == "`` foo` ``"
    assert pytilpack.markdown.inline_code("foo``bar") == "```foo``bar```"
