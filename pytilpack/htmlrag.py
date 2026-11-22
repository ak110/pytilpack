# clean_htmlはHtmlRAGのtoolkitから切り出して独自に拡張したもの。
# https://github.com/plageon/HtmlRAG/blob/main/toolkit/LICENSE
# https://github.com/plageon/HtmlRAG/blob/main/toolkit/htmlrag/html_utils.py

__lazy_modules__ = ["bs4", "httpx", "importlib.metadata", "pytilpack.functools", "re", "warnings"]

import importlib.metadata
import re
import warnings

import bs4
import httpx

import pytilpack.functools

DEFAULT_ACCEPT = "text/markdown,text/plain;q=0.9,text/html,application/xhtml+xml,application/xml;q=0.8,*/*;q=0.7"


def fetch_url(
    url: str,
    no_verify: bool = False,
    accept: str = DEFAULT_ACCEPT,
    user_agent: str | None = None,
    raw: bool = False,
) -> str:
    if user_agent is None:
        user_agent = get_default_user_agent()

    try:
        r = _get(url, headers={"Accept": accept, "User-Agent": user_agent}, verify=not no_verify)
    except httpx.HTTPStatusError as e:
        r = e.response

    return _process_fetched_response(url, r.status_code, r.headers.get("Content-Type"), r.text, raw=raw)


_RETRY_STATUS_CODES = (408, 429, 500, 502, 503, 504, 529)


@pytilpack.functools.retry(includes=(httpx.TransportError, httpx.HTTPStatusError), retry_status_codes=_RETRY_STATUS_CODES)
def _get(url: str, headers: dict[str, str], verify: bool) -> httpx.Response:
    r = httpx.get(url, headers=headers, verify=verify, follow_redirects=True)
    if r.status_code in _RETRY_STATUS_CODES:
        r.raise_for_status()
    return r


def _process_fetched_response(url: str, status_code: int, content_type: str | None, text: str, raw: bool = False) -> str:
    if status_code != 200:
        raise RuntimeError(
            f"URL {url} の取得に失敗しました。Status: {status_code}。URLとアクセス権を確かめて再試行する\n{text}"
        )

    if content_type is None:
        content_type = "text/html"
    if "html" in content_type:
        return text if raw else clean_html(text, aggressive=True, keep_title=True, keep_href=True)
    if content_type.startswith("text/") or "application/xml" in content_type or "application/json" in content_type:
        return text

    raise RuntimeError(
        f"URL {url} は扱えない形式です。Content-Type: {content_type}。テキスト・HTML・JSON・XML以外は取得できない"
    )


def get_default_user_agent():
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
    for script in soup.find_all("script"):
        assert isinstance(script, bs4.Tag)
        if script.get("type") != "application/json":
            script.decompose()
    for style in soup.find_all("style"):
        style.decompose()
    if aggressive:
        for el in soup.find_all(["nav", "header", "footer", "aside", "dialog"]):
            el.decompose()
    if not keep_title:
        for title in soup.find_all("title"):
            title.decompose()
    for tag in soup.find_all(recursive=True):
        if isinstance(tag, bs4.Tag):
            if keep_href and tag.name == "a":
                tag.attrs = {k: v for k, v in tag.attrs.items() if k in ("href",)}
            elif tag.name == "script":
                tag.attrs = {k: v for k, v in tag.attrs.items() if k in ("type",)}
            else:
                tag.attrs = {}
    while True:
        removed = False
        for tag in soup.find_all():
            if not tag.text.strip():
                tag.decompose()
                removed = True
        if not removed:
            break
    comments = soup.find_all(string=lambda text: isinstance(text, bs4.Comment))
    for comment in comments:
        comment.extract()

    def concat_text(text):
        text = "".join(text.split("\n"))
        text = "".join(text.split("\t"))
        text = "".join(text.split(" "))
        return text

    for tag in soup.find_all():
        if isinstance(tag, bs4.Tag):
            children = [child for child in tag.contents if not isinstance(child, str)]
            if len(children) == 1:
                tag_text = tag.get_text()
                child_text = "".join([child.get_text() for child in tag.contents if not isinstance(child, str)])
                if concat_text(child_text) == concat_text(tag_text):
                    tag.replace_with_children()

    res = str(soup)

    if aggressive:
        res = re.sub(r"</?(html|head|body|div|span)>", "", res)

    lines = [line for line in res.split("\n") if line.strip()]
    res = "\n".join(lines)

    return res


def _clean_xml(html: str) -> str:
    html = re.sub(r"<\?xml.*?>", "", html)
    html = re.sub(r"<!DOCTYPE.*?>", "", html)
    html = re.sub(r"<!doctype.*?>", "", html)
    return html
