"""Web関連のユーティリティ集。"""

__lazy_modules__ = [
    "html5lib",
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
import html5lib.constants
import werkzeug.http

import pytilpack.http

logger = logging.getLogger(__name__)

# RFC3986のpchar相当（query/fragmentを含まない）の許可文字集合
# 英数字 / - _ . ~ / : @ ! $ & ' ( ) * + , ; = %
_FORWARDED_PREFIX_ALLOWED = re.compile(r"^[a-zA-Z0-9\-_.~/:%@!$&'()*+,;=]*$")
# 制御文字（CR/LF/NUL等）の検出用
_CONTROL_CHAR = re.compile(r"[\x00-\x1f\x7f]")


def get_trusted_header_value(values: typing.Iterable[str], trusted_hops: int) -> str | None:
    """複数行のカンマ区切りヘッダーから信頼ホップの値を取得する。

    quoted-string内のカンマとエスケープはWerkzeugのHTTPパーサーで扱う。
    """
    if trusted_hops == 0:
        return None
    parsed = [item for value in values for item in werkzeug.http.parse_list_header(value)]
    return parsed[-trusted_hops] if len(parsed) >= trusted_hops else None


def validate_forwarded_prefix(value: str) -> str | None:
    """X-Forwarded-Prefixヘッダー値を検証し、正規化したprefixを返す。

    受け入れ時は末尾の``/``を除去した値を返す（先頭の``/``は保持する）。
    ``/``単独の場合もNoneを返す（prefix無し相当のため）。

    不正条件:
        - 空文字列
        - 先頭が``/``でない
        - ``//``で始まる（プロトコル相対形式）
        - CR/LF/NUL等の制御文字を含む
        - 許可文字集合外の文字を含む（RFC3986のpchar相当。query/fragmentは含めない）

    許可文字集合: 英数字 / ``-`` ``_`` ``.`` ``~`` ``/`` ``:`` ``@`` ``!`` ``$``
    ``&`` ``'`` ``(`` ``)`` ``*`` ``+`` ``,`` ``;`` ``=`` ``%``

    Args:
        value: 検証対象の文字列

    Returns:
        正規化したprefix（末尾``/``除去済み）、不正値または``/``単独の場合はNone
    """
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
        # "/" 単独だった場合
        return None
    return normalized


class PrefixPinner:
    """X-Forwarded-Prefixのpin管理。

    初回有効値のみ``apply``コールバックへ反映し、以降は固定する。
    攻撃者制御のヘッダー値でCookie発行パス等のアプリ全体設定が
    リクエストごとに書き換わる経路を断つための共通ロジックであり、
    Flask/QuartのProxyFix実装間で共有する。
    """

    def __init__(self, apply: typing.Callable[[str], None], warn: typing.Callable[[str], None]) -> None:
        """初期化する。

        Args:
            apply: pin確定時にprefixを反映するコールバック。
            warn: pin済み値と異なる値を受信した際の警告出力コールバック。

        """
        self._apply = apply
        self._warn = warn
        self._lock = threading.Lock()
        self._pinned_prefix: str | None = None
        self._prefix_pinned = False

    def initialize(self, static_prefix: str | None) -> None:
        """``static_prefix``指定時に初期pinする。

        Args:
            static_prefix: 起動時に確定させるprefix。Noneの場合は何もしない。

        Raises:
            ValueError: static_prefixが不正な場合。

        """
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
        """リクエストごとのprefixを初回のみ反映し、以降は不一致を警告する。"""
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
    """X-Forwarded-Hostヘッダー値を検証する。

    受け入れ時はそのまま返す。

    不正条件:
        - 空文字列
        - ``//``で始まる
        - CR/LF/NUL等の制御文字を含む
        - 空白を含む
        - ``[``で始まるがその値に``]``が含まれない（不完全なIPv6形式）

    Args:
        value: 検証対象の文字列

    Returns:
        valueそのまま、不正値の場合はNone
    """
    if not value:
        return None
    if value.startswith("//"):
        return None
    if _CONTROL_CHAR.search(value):
        return None
    if any(c.isspace() for c in value):
        return None
    # [で始まる場合は]を含まない不完全なIPv6形式を拒否する
    if value.startswith("[") and "]" not in value:
        return None
    return value


def is_host_in_trusted(host_value: str, trusted_hosts: typing.Iterable[str]) -> bool:
    """ホスト値（ポート含む可能性あり）を許可リストと照合する。

    ホスト値からホスト名部分のみを抽出して許可リストと突き合わせる。
    ポート番号は無視する。IPv6アドレス（``[::1]:8080``形式）にも対応する。

    Args:
        host_value: 検証対象のホスト値。``host:port``または``[ipv6]:port``形式を含む
        trusted_hosts: 許可するホスト名のイテラブル

    Returns:
        ホスト名が許可リストに含まれる場合True
    """
    # IPv6アドレスの解析: [::1]:8080 → ::1
    if host_value.startswith("["):
        bracket_end = host_value.find("]")
        host = host_value[1:bracket_end] if bracket_end != -1 else host_value
    elif ":" in host_value:
        host = host_value.rsplit(":", 1)[0]
    else:
        host = host_value

    return host in set(trusted_hosts)


class RouteInfo(typing.NamedTuple):
    """ルーティング情報を保持するクラス。

    Flask/Quartなど、`<name>` / `<type:name>` 形式のURLルールを扱うフレームワーク向け。

    Attributes:
        endpoint: エンドポイント名
        url_parts: URLのパーツのリスト
        arg_names: URLパーツの引数名のリスト
    """

    endpoint: str
    url_parts: list[str]
    arg_names: list[str]


_ARG_REGEX = re.compile(r"<([^>]+)>")  # <name> <type:name> にマッチするための正規表現
_SPLIT_REGEX = re.compile(r"<[^>]+>")  # re.splitのためグループ無しにした版


def build_next_url(script_root: str, path: str, query_string: str) -> str:
    """ログイン後遷移用のnextパラメーター用のURLを組み立てる。

    Flask/Quartの`request`情報を引数で受け取り、フレームワーク非依存で処理する。

    Args:
        script_root: リクエストのscript_root
        path: リクエストパス
        query_string: クエリ文字列（デコード済み）

    Returns:
        nextパラメーター用のURL
    """
    base = script_root + path
    return f"{base}?{query_string}" if query_string else base


def is_prefer_markdown(accept_header: str) -> bool:
    """AcceptヘッダーでmarkdownがHTMLより優先されているかを返す。

    参考: <https://vercel.com/blog/making-agent-friendly-pages-with-content-negotiation>

    Args:
        accept_header: Acceptヘッダーの値

    Returns:
        markdownがHTMLより優先されている場合True、そうでなければFalse
    """
    # text/htmlを先頭にすることで、同一quality時はHTMLを優先する（従来と同じ挙動）
    result = pytilpack.http.select_accept(accept_header, ["text/html", "text/markdown", "text/plain"])
    return result in ("text/markdown", "text/plain")


def build_routes(
    rules: typing.Iterable[typing.Any],
    application_root: str | None,
) -> list[RouteInfo]:
    """url_map.iter_rules()相当のイテラブルからRouteInfoのリストを構築する。

    Args:
        rules: 各要素が`endpoint`と`rule`属性を持つルーティングオブジェクト。
        application_root: アプリケーションルートパス。Noneや"/"の場合は無視する。

    Returns:
        `arg_names`の長さ降順でソートされたRouteInfoのリスト。
    """
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
    """静的ファイルのURLを生成する共通処理。

    Flask/Quartから共通で呼び出す。url_for呼び出しはフレームワークごとに異なるため
    callable経由で受け取る。キャッシュはフレームワーク側で保持する辞書を受け取る。

    Args:
        static_folder: 静的ファイルのディレクトリ
        filename: 静的ファイルのファイル名
        debug: デバッグモードかどうか
        cache_busting: キャッシュバスティングを有効にするかどうか
        cache_timestamp: ファイル最終更新日時のキャッシュ可否
        url_for_static: `url_for("static", filename=..., **kwargs)`相当の関数
        timestamp_cache: プロセス単位のタイムスタンプキャッシュ辞書
        **kwargs: url_for_staticに渡す追加引数

    Returns:
        静的ファイルのURL
    """
    if not cache_busting:
        return url_for_static(filename=filename, **kwargs)

    assert static_folder is not None, "static_folder is None"
    filepath = pathlib.Path(static_folder) / filename
    try:
        # ファイルの最終更新日時のキャッシュを利用するか否か
        if cache_timestamp is True or (cache_timestamp == "when_not_debug" and not debug):
            # キャッシュを使う
            timestamp = timestamp_cache.get(str(filepath))
            if timestamp is None:
                timestamp = int(filepath.stat().st_mtime)
                timestamp_cache[str(filepath)] = timestamp
        else:
            # キャッシュを使わない
            timestamp = int(filepath.stat().st_mtime)

        return url_for_static(filename=filename, v=timestamp, **kwargs)
    except OSError:
        # ファイルが存在しない場合などは通常のURLを返す
        return url_for_static(filename=filename, **kwargs)


def get_safe_url(target: str | None, host_url: str, default_url: str) -> str:
    """ログイン時のリダイレクトとして安全なURLを返す。

    Args:
        target: リダイレクト先のURL
        host_url: ホストのURL
        default_url: デフォルトのURL

    Returns:
        安全なURL
    """
    if target is None or target == "":
        return default_url
    ref_url = urllib.parse.urlparse(host_url)
    test_url = urllib.parse.urlparse(urllib.parse.urljoin(host_url, target))
    if test_url.scheme not in ("http", "https") or ref_url.netloc != test_url.netloc:
        logger.warning(f"Invalid next url: {target}. Redirecting to default_url instead (no action needed).")
        return default_url
    return target


def check_status_code(status_code: int, valid_status_code: int) -> None:
    """ステータスコードのチェック。"""
    if status_code != valid_status_code:
        raise AssertionError(f"ステータスコードエラー: {status_code} != {valid_status_code}")


def check_content_type(content_type: str, valid_content_types: str | typing.Iterable[str] | None) -> None:
    """Content-Typeのチェック。"""
    if valid_content_types is None:
        return None
    if isinstance(valid_content_types, str):
        valid_content_types = [valid_content_types]
    # ; charset=utf-8などが付いている場合があるため、簡易的にstartswithでチェックする
    if not any(content_type.startswith(c) for c in valid_content_types):
        raise AssertionError(f"Content-Typeエラー: {content_type} != {valid_content_types}")
    return None


def check_html(input_stream: typing.Any, strict: bool = False) -> None:
    """HTMLの字句・木構築時の構文エラーを診断する。

    html5libの診断に現行のselect解析規則を補って報告する。
    内容モデルや属性値など、HTML仕様への適合全体の検証は行わない。
    ただし``template``要素の範囲（最も外側の開始タグから対応する終了タグまで）にあるエラーは報告しない。
    html5lib 1.1は``template``要素の構文規則を持たず、``select``や表の中の``template``、
    行や列を内容に持つ``template``など、正しいHTMLに対してもエラーを記録するためである。
    このため``template``の内容にある本物の構文誤りも報告されない。
    対応する終了タグのない``template``は除外しない。

    Args:
        input_stream: 検査するHTML（``str``・``bytes``・ファイル風オブジェクト）。
        strict: Trueの場合はエラー時に``AssertionError``を送出し、Falseの場合は警告ログを出力して処理を継続する。

    """
    parser = _HTMLDiagnosticParser()
    _ = parser.parse(input_stream)
    if len(parser.errors) == 0:
        return
    errors = [
        f"{position}: {html5lib.constants.E[errorcode] % datavars}"
        for position, errorcode, datavars in parser.errors
        if not any(start <= position <= end for start, end in parser.template_ranges)
    ]
    if len(errors) > 0:
        if strict:
            error_str = "\n".join(errors)
            raise AssertionError(f"HTMLエラー: 報告位置のHTMLを修正してください。\n{error_str}")
        for error in errors:
            logger.warning(f"HTMLエラー: 処理を継続しました。報告位置のHTMLを修正してください。{error}")


class _HTMLDiagnosticParser(html5lib.HTMLParser):
    """html5lib 1.1のphase・tree・tokenizer位置を共有する診断用パーサー。"""

    def __init__(self) -> None:
        self.template_ranges: list[tuple[tuple[int, int], tuple[int, int]]] = []
        self.template_starts: list[tuple[int, int]] = []
        super().__init__()
        self.phases["inBody"] = _InBodyPhase(self, self.phases["inBody"])
        # resetInsertionModeも現行のin body解析へ戻す。
        self.phases["inSelect"] = self.phases["inBody"]
        self.phases["inSelectInTable"] = self.phases["inBody"]

    def reset(self) -> None:
        """文字コード変更による再解析でも診断と境界を同時に初期化する。"""
        self.template_ranges.clear()
        self.template_starts.clear()
        super().reset()


class _InBodyPhase:
    """現行select規則を補い、HTMLとして処理されたtemplateの位置を記録する。

    html5lib 1.1のmainLoopによる名前空間・挿入モードの選択と再処理に従う。
    phaseの内部メソッド、treeのスコープと暗黙終了、tokenizer.streamへ依存する。
    仕様: https://html.spec.whatwg.org/multipage/parsing.html#parsing-main-inbody
    """

    def __init__(self, parser: _HTMLDiagnosticParser, phase: typing.Any) -> None:
        self.parser = parser
        self.phase = phase
        self.tree = phase.tree

    def __getattr__(self, name: str) -> typing.Any:
        return getattr(self.phase, name)

    def processStartTag(self, token: dict[str, typing.Any]) -> typing.Any:
        """HTMLの開始タグへselectのスコープと暗黙終了を適用する。"""
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
        """HTMLの終了タグへselectスコープとtemplate境界を適用する。"""
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
