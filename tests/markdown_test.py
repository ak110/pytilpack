import html
import re

import pytilpack.markdown


def test_markdownfy_basic():
    text = "# Hello\n\nThis is a test."
    result = pytilpack.markdown.markdownfy(text)
    assert ">Hello</h1>" in result
    assert "<p>This is a test.</p>" in result

    assert pytilpack.markdown.markdownfy("") == ""

    code = 'print("Hello")'
    result = pytilpack.markdown.markdownfy(f"```\n{code}\n```")
    assert [html.unescape(body) for body in re.findall(r"<pre><code>(.*?)</code></pre>", result, re.S)] == [f"{code}\n"]

    text = """| Left | Right | Center |
|:----|----:|:----:|
| 1 | 2 | 3 |"""
    result = pytilpack.markdown.markdownfy(text)
    assert "<table>" in result
    assert re.findall(r'<(th|td) style="text-align: (\w+);">([^<]+)</\1>', result) == [
        ("th", "left", "Left"),
        ("th", "right", "Right"),
        ("th", "center", "Center"),
        ("td", "left", "1"),
        ("td", "right", "2"),
        ("td", "center", "3"),
    ]


def test_markdownfy_with_html_tag():
    fragment = "<script>alert('test')</script>"
    result = pytilpack.markdown.markdownfy(fragment)
    assert "<script>" not in result
    assert "&lt;script&gt;" in result

    fragment = "<details><summary>サマリ</summary>詳細</details>"
    result = pytilpack.markdown.markdownfy(fragment)
    assert fragment in result

    fragment = "<think>最近流行りのreasoning</think>結果"
    result = pytilpack.markdown.markdownfy(fragment)
    assert "<think>" not in result
    assert "&lt;think&gt;" in result


def test_markdownfy_with_malicious_content():
    text = "[click me](javascript:alert('test'))"
    result = pytilpack.markdown.markdownfy(text)
    assert "javascript:" not in result
    assert "click me" in result

    result = pytilpack.markdown.markdownfy("[documentation](https://example.com/docs)")
    assert '<a href="https://example.com/docs">documentation</a>' in result


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
