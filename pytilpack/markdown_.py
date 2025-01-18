"""markdown関連。"""

import typing

import bleach
import markdown


def markdownfy(
    text: str,
    extensions: typing.Sequence[str | markdown.Extension] | None = None,
    extension_configs: (
        typing.Mapping[str, typing.Mapping[str, typing.Any]] | None
    ) = None,
    tab_length: int | None = 2,
    **kwargs,
) -> str:
    """Markdown変換。"""
    if extensions is None:
        extensions = ["markdown.extensions.extra", "markdown.extensions.toc"]
    if extension_configs is None:
        extension_configs = {"toc": {"title": "目次", "permalink": True}}
    return _sanitize_html(
        markdown.markdown(
            text,
            extensions=extensions,
            extension_configs=extension_configs,
            tab_length=tab_length,
            **kwargs,
        )
    )


def _sanitize_html(text: str) -> str:
    """HTMLタグのサニタイズ。"""
    return bleach.clean(
        text,
        tags={
            "a",
            "abbr",
            "acronym",
            "address",
            "article",
            "aside",
            "b",
            "big",
            "blockquote",
            "br",
            "cite",
            "code",
            "del",
            "details",
            "dfn",
            "div",
            "em",
            "footer",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "header",
            "hr",
            "i",
            "img",
            "ins",
            "kbd",
            "li",
            "mark",
            "nav",
            "ol",
            "p",
            "pre",
            "q",
            "s",
            "samp",
            "section",
            "small",
            "span",
            "strong",
            "sub",
            "summary",
            "sup",
            "table",
            "tbody",
            "td",
            "th",
            "thead",
            "time",
            "tr",
            "tt",
            "u",
            "ul",
            "var",
        },
        attributes={
            "a": ["href", "title", "target", "rel"],
            "abbr": ["title"],
            "acronym": ["title"],
            "details": ["open"],
            "img": ["src", "alt", "title"],
            "td": ["colspan", "rowspan"],
            "th": ["colspan", "rowspan"],
            "time": ["datetime"],
            "tr": ["rowspan"],
        },
        protocols=bleach.ALLOWED_PROTOCOLS,
    )
