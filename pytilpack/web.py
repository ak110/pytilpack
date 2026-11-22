__lazy_modules__ = [
    "html5lib",
    "html5lib._tokenizer",
    "html5lib.constants",
    "logging",
    "pathlib",
    "pytilpack.http",
    "re",
    "threading",
    "typing",
    "urllib.parse",
    "werkzeug.http",
]

import logging
import pathlib
import re
import threading
import typing
import urllib.parse

import html5lib
import html5lib._tokenizer
import html5lib.constants
import werkzeug.http

import pytilpack.http

logger = logging.getLogger(__name__)

_FORWARDED_PREFIX_ALLOWED = re.compile(r"^[a-zA-Z0-9\-_.~/:%@!$&'()*+,;=]*$")
_CONTROL_CHAR = re.compile(r"[\x00-\x1f\x7f]")


def get_trusted_header_value(values: typing.Iterable[str], trusted_hops: int) -> str | None:
    if trusted_hops == 0:
        return None
    parsed = [item for value in values for item in werkzeug.http.parse_list_header(value)]
    return parsed[-trusted_hops] if len(parsed) >= trusted_hops else None


def validate_forwarded_prefix(value: str) -> str | None:
    if not value:
        return None
    if not value.startswith("/"):
        return None
    if value.startswith("//"):
        return None
    if _CONTROL_CHAR.search(value):
        return None
    if not _FORWARDED_PREFIX_ALLOWED.match(value):
        return None
    normalized = value.rstrip("/")
    if not normalized:
        return None
    return normalized


class PrefixPinner:
    def __init__(self, apply: typing.Callable[[str], None], warn: typing.Callable[[str], None]) -> None:
        self._apply = apply
        self._warn = warn
        self._lock = threading.Lock()
        self._pinned_prefix: str | None = None
        self._prefix_pinned = False

    def initialize(self, static_prefix: str | None) -> None:
        if static_prefix is None:
            return
        validated = validate_forwarded_prefix(static_prefix)
        if validated is None:
            raise ValueError(
                f"static_prefixが不正: {static_prefix!r}。"
                "/で始まり（//は不可）、制御文字やquery・fragmentを含まないパス（例: /app）を指定する"
            )
        self._apply(validated)
        self._pinned_prefix = validated
        self._prefix_pinned = True

    def pin(self, prefix: str) -> None:
        if not self._prefix_pinned:
            with self._lock:
                if not self._prefix_pinned:
                    self._apply(prefix)
                    self._pinned_prefix = prefix
                    self._prefix_pinned = True
                    return
        if self._pinned_prefix != prefix:
            self._warn(
                f"X-Forwarded-Prefixがpin済みの値と異なります: pinned={self._pinned_prefix!r}, received={prefix!r}。"
                "pin済みの値を維持して処理を続ける。プロキシが送るX-Forwarded-Prefixの設定を見直す"
            )


def validate_forwarded_host(value: str) -> str | None:
    if not value:
        return None
    if value.startswith("//"):
        return None
    if _CONTROL_CHAR.search(value):
        return None
    if any(c.isspace() for c in value):
        return None
    if value.startswith("[") and "]" not in value:
        return None
    return value


def is_host_in_trusted(host_value: str, trusted_hosts: typing.Iterable[str]) -> bool:
    if host_value.startswith("["):
        bracket_end = host_value.find("]")
        host = host_value[1:bracket_end] if bracket_end != -1 else host_value
    elif ":" in host_value:
        host = host_value.rsplit(":", 1)[0]
    else:
        host = host_value

    return host in set(trusted_hosts)


class RouteInfo(typing.NamedTuple):
    endpoint: str
    url_parts: list[str]
    arg_names: list[str]


_ARG_REGEX = re.compile(r"<([^>]+)>")
_SPLIT_REGEX = re.compile(r"<[^>]+>")


def build_next_url(script_root: str, path: str, query_string: str) -> str:
    base = script_root + path
    return f"{base}?{query_string}" if query_string else base


def is_prefer_markdown(accept_header: str) -> bool:
    result = pytilpack.http.select_accept(accept_header, ["text/html", "text/markdown", "text/plain"])
    return result in ("text/markdown", "text/plain")


def build_routes(
    rules: typing.Iterable[typing.Any],
    application_root: str | None,
) -> list[RouteInfo]:
    output: list[RouteInfo] = []
    for r in rules:
        endpoint = str(r.endpoint)
        rule = r.rule if application_root == "/" or not application_root else f"{application_root}{r.rule}"
        url_parts = [str(part) for part in _SPLIT_REGEX.split(rule)]
        arg_names = [str(x.split(":")[-1]) for x in _ARG_REGEX.findall(rule)]
        output.append(RouteInfo(endpoint, url_parts, arg_names))
    return sorted(output, key=lambda x: len(x[2]), reverse=True)


def resolve_static_url(
    static_folder: str | None,
    filename: str,
    debug: bool,
    cache_busting: bool,
    cache_timestamp: bool | typing.Literal["when_not_debug"],
    url_for_static: typing.Callable[..., str],
    timestamp_cache: dict[str, int],
    **kwargs: typing.Any,
) -> str:
    if not cache_busting:
        return url_for_static(filename=filename, **kwargs)

    assert static_folder is not None, "static_folder is None"
    filepath = pathlib.Path(static_folder) / filename
    try:
        if cache_timestamp is True or (cache_timestamp == "when_not_debug" and not debug):
            timestamp = timestamp_cache.get(str(filepath))
            if timestamp is None:
                timestamp = int(filepath.stat().st_mtime)
                timestamp_cache[str(filepath)] = timestamp
        else:
            timestamp = int(filepath.stat().st_mtime)

        return url_for_static(filename=filename, v=timestamp, **kwargs)
    except OSError:
        return url_for_static(filename=filename, **kwargs)


def get_safe_url(target: str | None, host_url: str, default_url: str) -> str:
    if target is None or target == "":
        return default_url
    ref_url = urllib.parse.urlparse(host_url)
    test_url = urllib.parse.urlparse(urllib.parse.urljoin(host_url, target))
    if test_url.scheme not in ("http", "https") or ref_url.netloc != test_url.netloc:
        logger.warning(f"Invalid next url: {target}. Redirecting to default_url instead (no action needed).")
        return default_url
    return target


def check_status_code(status_code: int, valid_status_code: int) -> None:
    if status_code != valid_status_code:
        raise AssertionError(f"ステータスコードエラー: {status_code} != {valid_status_code}")


def check_content_type(content_type: str, valid_content_types: str | typing.Iterable[str] | None) -> None:
    if valid_content_types is None:
        return None
    if isinstance(valid_content_types, str):
        valid_content_types = [valid_content_types]
    if not any(content_type.startswith(c) for c in valid_content_types):
        raise AssertionError(f"Content-Typeエラー: {content_type} != {valid_content_types}")
    return None


def check_html(input_stream: typing.Any, strict: bool = False) -> None:
    parser = _HTMLDiagnosticParser()
    _ = parser.parse(input_stream)
    if len(parser.errors) == 0:
        return
    errors = [
        f"{position}: {html5lib.constants.E[errorcode] % datavars}"
        for position, errorcode, datavars in parser.errors
        # html5lib 1.1はtemplate要素の構文規則を持たず正しいHTMLにもエラーを記録するため、templateの範囲を除外する。
        if not any(start <= position <= end for start, end in parser.template_ranges)
    ]
    if len(errors) > 0:
        if strict:
            error_str = "\n".join(errors)
            raise AssertionError(f"HTMLエラー: 報告位置のHTMLを修正してください。\n{error_str}")
        for error in errors:
            logger.warning(f"HTMLエラー: 処理を継続しました。報告位置のHTMLを修正してください。{error}")


# html5lib 1.1のconsumeEntityは、&の次がASCII英数字・#以外でもexpected-named-entityを積む。
# 現行仕様のCharacter reference stateはこの場合に文字参照を開始しないため、そのエラーだけを除く。
# https://html.spec.whatwg.org/multipage/parsing.html#character-reference-state
class _DiagnosticTokenizer(html5lib._tokenizer.HTMLTokenizer):  # pylint: disable=protected-access
    def consumeEntity(self, allowedChar: str | None = None, fromAttribute: bool = False) -> None:
        first = self.stream.char()
        self.stream.unget(first)
        queued = len(self.tokenQueue)
        super().consumeEntity(allowedChar, fromAttribute)
        if first == "#" or first in html5lib.constants.asciiLetters or first in html5lib.constants.digits:
            return
        added = [self.tokenQueue.pop() for _ in range(len(self.tokenQueue) - queued)][::-1]
        parse_error = html5lib.constants.tokenTypes["ParseError"]
        self.tokenQueue.extend(
            token for token in added if not (token.get("type") == parse_error and token.get("data") == "expected-named-entity")
        )


class _HTMLDiagnosticParser(html5lib.HTMLParser):
    # html5lib 1.1の_parseと同じ手順。トークナイザーの型を差し替える公開手段が無いため写している。
    def _parse(
        self,
        stream: typing.Any,
        innerHTML: bool = False,
        container: str = "div",
        scripting: bool = False,
        **kwargs: typing.Any,
    ) -> None:
        # pylint: disable=attribute-defined-outside-init,protected-access
        self.innerHTMLMode = innerHTML
        self.container = container
        self.scripting = scripting
        self.tokenizer = _DiagnosticTokenizer(stream, parser=self, **kwargs)
        self.reset()
        try:
            self.mainLoop()
        except html5lib.constants._ReparseException:
            self.reset()
            self.mainLoop()

    def __init__(self) -> None:
        self.template_ranges: list[tuple[tuple[int, int], tuple[int, int]]] = []
        self.template_starts: list[tuple[int, int]] = []
        super().__init__()
        self.phases["inBody"] = _InBodyPhase(self, self.phases["inBody"])
        self.phases["inSelect"] = self.phases["inBody"]
        self.phases["inSelectInTable"] = self.phases["inBody"]

    def reset(self) -> None:
        self.template_ranges.clear()
        self.template_starts.clear()
        super().reset()


class _InBodyPhase:
    def __init__(self, parser: _HTMLDiagnosticParser, phase: typing.Any) -> None:
        self.parser = parser
        self.phase = phase
        self.tree = phase.tree

    def __getattr__(self, name: str) -> typing.Any:
        return getattr(self.phase, name)

    def processStartTag(self, token: dict[str, typing.Any]) -> typing.Any:
        name = token["name"]
        in_select = self.tree.elementInScope("select")
        if name == "template":
            self.parser.template_starts.append(self.parser.tokenizer.stream.position())
        if name == "select":
            if in_select:
                self.parser.parseError("unexpected-select-in-select")
                self._pop_select()
            else:
                self.tree.reconstructActiveFormattingElements()
                self.tree.insertElement(token)
                self.parser.framesetOK = False
            return None
        if in_select and name == "input":
            self.parser.parseError("unexpected-input-in-select")
            self._pop_select()
        if in_select and name in ("option", "optgroup", "hr"):
            self.tree.generateImpliedEndTags(exclude="optgroup" if name == "option" else None)
            if self.tree.elementInScope("option") or (name != "option" and self.tree.elementInScope("optgroup")):
                self.parser.parseError("unexpected-start-tag", {"name": name})
        return self.phase.processStartTag(token)

    def processEndTag(self, token: dict[str, typing.Any]) -> typing.Any:
        name = token["name"]
        if name == "template" and self.parser.template_starts:
            start = self.parser.template_starts.pop()
            if not self.parser.template_starts:
                self.parser.template_ranges.append((start, self.parser.tokenizer.stream.position()))
        if name == "select":
            if not self.tree.elementInScope("select"):
                self.parser.parseError("unexpected-end-tag", {"name": name})
                return None
            self.tree.generateImpliedEndTags()
            if self.tree.openElements[-1].name != name:
                self.parser.parseError("end-tag-too-early", {"name": name})
            self._pop_select()
            return None
        return self.phase.processEndTag(token)

    def _pop_select(self) -> None:
        while self.tree.openElements.pop().name != "select":
            pass
