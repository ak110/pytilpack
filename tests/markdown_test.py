"""テストコード。"""

import pytilpack.markdown_


def test_markdownfy_basic():
    """基本的なMarkdown変換のテスト。"""
    # 基本的な変換
    text = "# Hello\n\nThis is a test."
    result = pytilpack.markdown_.markdownfy(text)
    assert ">Hello</h1>" in result
    assert "<p>This is a test.</p>" in result

    # 空文字列
    assert pytilpack.markdown_.markdownfy("") == ""

    # fenced_code
    text = """```
    def hello():
        print("Hello")
    ```"""
    result = pytilpack.markdown_.markdownfy(text)
    assert "<code>" in result

    # テーブル(左寄せ,右寄せ,中央寄せ)
    text = """| Left | Right | Center |
|:----|----:|:----:|
| 1 | 2 | 3 |"""
    result = pytilpack.markdown_.markdownfy(text)
    assert "<table>" in result
    assert '<th style="text-align: left;">' in result
    assert '<th style="text-align: right;">' in result
    assert '<th style="text-align: center;">' in result
    assert '<td style="text-align: left;">' in result
    assert '<td style="text-align: right;">' in result
    assert '<td style="text-align: center;">' in result


def test_markdownfy_with_html_tag():
    """HTMLサニタイズのテスト。"""
    # スクリプトタグのエスケープ
    html = "<script>alert('test')</script>"
    result = pytilpack.markdown_.markdownfy(html)
    assert "<script>" not in result
    assert "&lt;script&gt;" in result

    # details/summaryタグは許可
    html = "<details><summary>サマリ</summary>詳細</details>"
    result = pytilpack.markdown_.markdownfy(html)
    assert html in result

    # HTMLに無いタグはエスケープ
    html = "<think>最近流行りのreasoning</think>結果"
    result = pytilpack.markdown_.markdownfy(html)
    assert "<think>" not in result
    assert "&lt;think&gt;" in result


def test_markdownfy_with_malicious_content():
    """悪意のある入力に対するテスト。"""
    # JavaScriptインジェクション
    text = "[click me](javascript:alert('test'))"
    result = pytilpack.markdown_.markdownfy(text)
    assert "javascript:" not in result
