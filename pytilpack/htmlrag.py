"""HtmlRAG関連。

clean_htmlだけを使用したい場合に依存関係が色々厳しいため切り出したものを用意しちゃう。

<https://github.com/plageon/HtmlRAG/blob/main/toolkit/README.md>
<https://github.com/plageon/HtmlRAG/blob/main/toolkit/htmlrag/html_utils.py>

"""

import re
import warnings

import bs4


def clean_html(
    html: str | bytes,
    aggressive: bool = False,
    keep_title: bool | None = None,
    keep_href: bool | None = None,
    remove_span: bool | None = None,
) -> str:
    """HTMLからLLM向けに不要なタグを削除する。

    Args:
        html: HTML文字列
        aggressive: より強力な削除を行うか否か。Defaults to False.
        keep_title: titleタグを残すか否か。Defaults to 'not aggressive'.
        keep_href: href属性を残すか否か。Defaults to 'not aggressive'.
        remove_span: spanタグを削除するか否か。(deprecated)

    Returns:
        処理後のHTML文字列

    """
    if remove_span is not None:
        warnings.warn(
            "remove_span is deprecated. Use aggressive=True to remove span tags.",
            DeprecationWarning,
            stacklevel=2,
        )
        aggressive = remove_span
    if keep_title is None:
        keep_title = not aggressive
    if keep_href is None:
        keep_href = not aggressive

    soup = bs4.BeautifulSoup(html, "html.parser")
    html = _simplify_html(
        soup, aggressive=aggressive, keep_title=keep_title, keep_href=keep_href
    )
    html = _clean_xml(html)
    return html


def _simplify_html(
    soup: bs4.BeautifulSoup, aggressive: bool, keep_title: bool, keep_href: bool
) -> str:
    for script in soup(["script", "style"]):
        script.decompose()
    # 独自拡張: メインコンテンツじゃなさそうなタグとtitleタグを削除
    if aggressive:
        for el in soup.find_all(["nav", "header", "footer", "aside", "dialog"]):
            el.decompose()
    if not keep_title:
        for title in soup.find_all("title"):
            title.decompose()
    #  remove all attributes
    for tag in soup.find_all(recursive=True):
        if isinstance(tag, bs4.Tag):
            # 独自拡張: hrefを残すオプションを追加
            if keep_href and tag.name == "a":
                tag.attrs = {"href": str(tag.get("href"))}  # href属性だけ残す
            else:
                tag.attrs = {}
    #  remove empty tags recursively
    while True:
        removed = False
        for tag in soup.find_all():
            if not tag.text.strip():
                tag.decompose()
                removed = True
        if not removed:
            break
    # ↓元々意味をなしてない？
    # #  remove href attributes
    # for tag in soup.find_all("a"):
    #     del tag["href"]
    #  remove comments
    comments = soup.find_all(string=lambda text: isinstance(text, bs4.Comment))
    for comment in comments:
        comment.extract()

    def concat_text(text):
        text = "".join(text.split("\n"))
        text = "".join(text.split("\t"))
        text = "".join(text.split(" "))
        return text

    # remove all tags with no text
    for tag in soup.find_all():
        if isinstance(tag, bs4.Tag):
            children = [child for child in tag.contents if not isinstance(child, str)]
            if len(children) == 1:
                tag_text = tag.get_text()
                child_text = "".join(
                    [
                        child.get_text()
                        for child in tag.contents
                        if not isinstance(child, str)
                    ]
                )
                if concat_text(child_text) == concat_text(tag_text):
                    tag.replace_with_children()
    #  if html is not wrapped in a html tag, wrap it

    res = str(soup)

    # 独自拡張。セマンティックな意味をあまり持たないタグ(html, head, body, div, span)を削除しちゃう。
    if aggressive:
        res = re.sub(r"</?(html|head|body|div|span)>", "", res)

    # remove empty lines
    lines = [line for line in res.split("\n") if line.strip()]
    res = "\n".join(lines)

    return res


def _clean_xml(html: str) -> str:
    # remove tags starts with <?xml
    html = re.sub(r"<\?xml.*?>", "", html)
    # remove tags starts with <!DOCTYPE
    html = re.sub(r"<!DOCTYPE.*?>", "", html)
    # remove tags starts with <!DOCTYPE
    html = re.sub(r"<!doctype.*?>", "", html)
    return html
