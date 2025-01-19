"""markdown関連。"""

import typing

import bleach
import bleach_allowlist
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

    html = markdown.markdown(
        text,
        extensions=extensions,
        extension_configs=extension_configs,
        tab_length=tab_length,
        **kwargs,
    )

    html = bleach.clean(
        html,
        tags=set(bleach_allowlist.generally_xss_safe) - {"detals"} | {"details"},
        attributes={
            "*": ["id", "title"],
            "a": ["href", "alt", "title", "target", "rel"],
            "details": ["open"],
            "img": ["src", "alt", "title"],
            "td": ["colspan", "rowspan"],
            "th": ["colspan", "rowspan"],
            "tr": ["rowspan"],
        },
        protocols=bleach.ALLOWED_PROTOCOLS,
    )

    return html
