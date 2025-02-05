"""markdown関連。"""

import typing

import bleach
import bleach.css_sanitizer
import markdown

ALLOWED_TAGS = {
    "a",
    "abbr",
    "acronym",
    "address",
    "area",
    "article",
    "aside",
    "b",
    "base",
    "basefont",
    "bdi",
    "bdo",
    "big",
    "blink",
    "blockquote",
    "br",
    "button",
    "caption",
    "center",
    "cite",
    "code",
    "col",
    "colgroup",
    "command",
    "content",
    "data",
    "datalist",
    "dd",
    "del",
    "details",
    "dfn",
    "dialog",
    "dir",
    "div",
    "dl",
    "dt",
    "element",
    "em",
    "fieldset",
    "figcaption",
    "figure",
    "font",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hgroup",
    "hr",
    "i",
    "image",
    "img",
    "input",
    "ins",
    "isindex",
    "kbd",
    "keygen",
    "label",
    "legend",
    "li",
    "listing",
    "main",
    "map",
    "mark",
    "marquee",
    "menu",
    "menuitem",
    "meter",
    "multicol",
    "nav",
    "nobr",
    "noembed",
    "noframes",
    "noscript",
    "ol",
    "optgroup",
    "option",
    "output",
    "p",
    "picture",
    "plaintext",
    "pre",
    "progress",
    "q",
    "rp",
    "s",
    "samp",
    "section",
    "select",
    "shadow",
    "small",
    "spacer",
    "span",
    "strike",
    "strong",
    "style",
    "sub",
    "summary",
    "sup",
    "table",
    "tbody",
    "td",
    "template",
    "textarea",
    "tfoot",
    "th",
    "thead",
    "time",
    "tr",
    "tt",
    "u",
    "ul",
    "var",
    "wbr",
}
"""許可するタグ。"""

ALLOWED_ATTRIBUTES = {
    "*": ["id", "title", "class", "style"],
    "a": ["href", "alt", "title", "target", "rel"],
    "details": ["open"],
    "img": ["src", "alt", "title", "width", "height"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
    "tr": ["rowspan"],
}
"""許可する属性。"""

ALLOWED_PROTOCOLS = {"http", "https", "mailto"}
"""許可するプロトコル。"""


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

    html = markdown.markdown(
        text,
        extensions=extensions,
        extension_configs=extension_configs,
        tab_length=tab_length,
        **kwargs,
    )

    html = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=bleach.css_sanitizer.CSSSanitizer(),
    )

    return html
