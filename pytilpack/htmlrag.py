"""HtmlRAG関連。

clean_htmlだけを使用したい場合に依存関係が色々厳しいため切り出したものを用意しちゃう。

<https://github.com/plageon/HtmlRAG/blob/main/toolkit/README.md>
<https://github.com/plageon/HtmlRAG/blob/main/toolkit/htmlrag/html_utils.py>

"""

import re

import bs4


def clean_html(html: str, remove_span: bool = False) -> str:
    """HTMLからLLM向けに不要なタグを削除する。

    Args:
        html: HTML文字列
        remove_span: spanタグを削除するか否か. Defaults to False.

    Returns:
        処理後のHTML文字列

    """
    soup = bs4.BeautifulSoup(html, "html.parser")
    html = _simplify_html(soup)
    html = _clean_xml(html)
    # おまけの独自拡張。spanタグは通常セマンティックな意味を持たないため削除しちゃう。
    if remove_span:
        html = html.replace("<span>", "").replace("</span>", "")
    return html


def _trim_path(path):
    #  is leaf, remove the tag
    if path["is_leaf"]:
        path["tag"].decompose()
        return
    #  not leaf, remove the text directly under the tag
    else:
        for c in path["tag"].contents:
            if not isinstance(c, bs4.element.Tag):
                # print(c)
                #  remove the text node
                c.extract()


def _truncate_input(html, chat_tokenizer, max_context_window=30000):
    if isinstance(html, list):
        html = " ".join(html)
    #  if html is longer than 30000 tokens, truncate it
    tokens = chat_tokenizer.tokenize(html)
    if len(tokens) > max_context_window:
        html = chat_tokenizer.convert_tokens_to_string(tokens[:max_context_window])
        # print(f"html truncated to {max_context_window} tokens")
    return html


def _simplify_html(soup, keep_attr: bool = False) -> str:
    for script in soup(["script", "style"]):
        script.decompose()
    #  remove all attributes
    if not keep_attr:
        for tag in soup.find_all(True):
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
    #  remove href attributes
    for tag in soup.find_all("a"):
        del tag["href"]
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

    # remove empty lines
    res = str(soup)
    lines = [line for line in res.split("\n") if line.strip()]
    res = "\n".join(lines)
    return res


def _clean_xml(html):
    # remove tags starts with <?xml
    html = re.sub(r"<\?xml.*?>", "", html)
    # remove tags starts with <!DOCTYPE
    html = re.sub(r"<!DOCTYPE.*?>", "", html)
    # remove tags starts with <!DOCTYPE
    html = re.sub(r"<!doctype.*?>", "", html)
    return html
