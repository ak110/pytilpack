"""HtmlRAG関連。

clean_htmlだけを使用したい場合に依存関係が色々厳しいため切り出したものを用意しちゃう。
ついでに少し独自拡張。

<https://github.com/plageon/HtmlRAG/blob/main/toolkit/README.md>
<https://github.com/plageon/HtmlRAG/blob/main/toolkit/LICENSE>
<https://github.com/plageon/HtmlRAG/blob/main/toolkit/htmlrag/html_utils.py>
"""

import importlib.metadata
import re
import warnings

import bs4
import httpx

DEFAULT_ACCEPT = "text/markdown,text/plain;q=0.9,text/html,application/xhtml+xml,application/xml;q=0.8,*/*;q=0.7"
"""Acceptヘッダーのデフォルト値。"""


def fetch_url(
    url: str,
    no_verify: bool = False,
    accept: str = DEFAULT_ACCEPT,
    user_agent: str | None = None,
) -> str:
    """URLからHTMLを取得し、簡略化して返します。

    Args:
        url: 取得するURL
        no_verify: SSL証明書の検証を無効化するかどうか
        accept: 受け入れるコンテンツタイプ
        user_agent: User-Agentヘッダー（未指定時はデフォルト値を使用）

    Returns:
        簡略化されたHTML内容

    Raises:
        Exception: HTTP取得やHTMLパースでエラーが発生した場合
    """
    if user_agent is None:
        user_agent = get_default_user_agent()

    r = httpx.get(
        url,
        headers={
            "Accept": accept,
            "User-Agent": user_agent,
        },
        verify=not no_verify,
        follow_redirects=True,
    )

    if r.status_code != 200:
        raise RuntimeError(f"URL {url} の取得に失敗しました。Status: {r.status_code}\n{r.text}")

    content_type = r.headers.get("Content-Type", "text/html")
    if (
        "text/markdown" in content_type
        or "text/plain" in content_type
        or "text/xml" in content_type
        or "application/xml" in content_type
        or "application/json" in content_type
    ):
        return r.text

    if "html" not in content_type:
        raise RuntimeError(f"URL {url} はHTMLではありません。Content-Type: {content_type}\n{r.text[:100]}...")

    content = r.text
    output = clean_html(
        content,
        aggressive=True,
        keep_title=True,
        keep_href=True,
    )
    return output


def get_default_user_agent():
    """デフォルトのUser-Agentヘッダーを取得する。"""
    version = importlib.metadata.version("pytilpack")
    user_agent = f"pytilpack/{version} (+https://github.com/ak110/pytilpack)"
    return user_agent


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
    html = _simplify_html(soup, aggressive=aggressive, keep_title=keep_title, keep_href=keep_href)
    html = _clean_xml(html)
    return html


def _simplify_html(soup: bs4.BeautifulSoup, aggressive: bool, keep_title: bool, keep_href: bool) -> str:
    # スクリプトタグの削除
    for script in soup.find_all("script"):
        # 独自拡張: <script type="application/json">は残す (github.comなど対策)
        assert isinstance(script, bs4.Tag)
        if script.get("type") != "application/json":
            script.decompose()
    # スタイルタグの削除
    for style in soup.find_all("style"):
        style.decompose()
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
                # href属性だけ残す
                tag.attrs = {k: v for k, v in tag.attrs.items() if k in ("href",)}
            elif tag.name == "script":
                # type属性だけ残す
                tag.attrs = {k: v for k, v in tag.attrs.items() if k in ("type",)}
            else:
                # 他のタグは全ての属性を削除
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
                child_text = "".join([child.get_text() for child in tag.contents if not isinstance(child, str)])
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
