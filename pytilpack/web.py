"""Web関係の一般的な処理をまとめたモジュール。"""

import logging
import pathlib
import re
import typing
import urllib.parse

import html5lib
import html5lib.constants

import pytilpack.http

logger = logging.getLogger(__name__)

# RFC3986のpchar相当（query/fragmentを含まない）の許可文字集合
# 英数字 / - _ . ~ / : @ ! $ & ' ( ) * + , ; = %
_FORWARDED_PREFIX_ALLOWED = re.compile(r"^[a-zA-Z0-9\-_.~/:%@!$&'()*+,;=]*$")
# 制御文字（CR/LF/NUL等）の検出用
_CONTROL_CHAR = re.compile(r"[\x00-\x1f\x7f]")


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
        logger.warning(f"Invalid next url: {target}")
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
    """HTMLのチェック。"""
    parser = html5lib.HTMLParser(debug=True)
    _ = parser.parse(input_stream)
    if len(parser.errors) > 0:
        errors = [
            f"{position}: {html5lib.constants.E[errorcode] % datavars}" for position, errorcode, datavars in parser.errors
        ]
        if strict:
            error_str = "\n".join(errors)
            raise AssertionError(f"HTMLエラー: {error_str}")
        for error in errors:
            logger.warning(f"HTMLエラー: {error}")
