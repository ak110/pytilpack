"""Quart関連のユーティリティ。"""

import copy
import json
import logging
import pathlib
import typing
import xml.etree.ElementTree

import hypercorn.typing
import quart

logger = logging.getLogger(__name__)


async def assert_bytes(
    response,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = None,
) -> bytes:
    """quartのテストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスボディ

    """
    response_body = await response.get_data()

    try:
        # ステータスコードチェック
        check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        check_content_type(response.content_type, content_type)
    except AssertionError as e:
        logger.info(f"{e}\n\n{response_body!r}")
        raise e

    return response_body


async def assert_html(
    response,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "__default__",
    tmp_path: pathlib.Path | None = None,
) -> str:
    """quartのテストコード用。

    html5libが必要なので注意。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type
        tmp_path: 一時ファイルを保存するディレクトリ

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスボディ (bs4.BeautifulSoup)

    """
    import html5lib

    response_body = (await response.get_data()).decode("utf-8")

    try:
        # ステータスコードチェック
        check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        if content_type == "__default__":
            content_type = ["text/html", "application/xhtml+xml"]
        check_content_type(response.content_type, content_type)

        # HTMLのチェック
        parser = html5lib.HTMLParser(strict=True, debug=True)
        try:
            _ = parser.parse(await response.get_data())
        except html5lib.html5parser.ParseError as e:
            raise AssertionError(f"HTMLエラー: {e}") from e
    except AssertionError as e:
        tmp_file_path = _create_temp_file(tmp_path, response_body)
        raise AssertionError(f"{e} (HTML: {tmp_file_path} )") from e

    return response_body


async def assert_json(
    response,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "application/json",
) -> dict[str, typing.Any]:
    """quartのテストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスのjson

    """
    response_body = (await response.get_data()).decode("utf-8")

    try:
        # ステータスコードチェック
        check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        check_content_type(response.content_type, content_type)

        # JSONのチェック
        try:
            data = json.loads(response_body)
        except Exception as e:
            raise AssertionError(f"JSONエラー: {e}") from e
    except AssertionError as e:
        logger.info(f"{e}\n\n{response_body!r}")
        raise e

    return data


async def assert_xml(
    response,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "__default__",
) -> str:
    """quartのテストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスのxml

    """
    response_body = (await response.get_data()).decode("utf-8")

    try:
        # ステータスコードチェック
        check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        if content_type == "__default__":
            content_type = ["text/xml", "application/xml"]
        check_content_type(response.content_type, content_type)

        # XMLのチェック
        try:
            _ = xml.etree.ElementTree.fromstring(response_body)
        except Exception as e:
            raise AssertionError(f"XMLエラー: {e}") from e
    except AssertionError as e:
        logger.info(f"{e}\n\n{response_body!r}")
        raise e

    return response_body


def check_status_code(status_code: int, valid_status_code: int) -> None:
    """ステータスコードのチェック。"""
    if status_code != valid_status_code:
        raise AssertionError(
            f"ステータスコードエラー: {status_code} != {valid_status_code}"
        )


def check_content_type(
    content_type: str, valid_content_types: str | typing.Iterable[str] | None
) -> None:
    """Content-Typeのチェック。"""
    if valid_content_types is None:
        return None
    if isinstance(valid_content_types, str):
        valid_content_types = [valid_content_types]
    if not any(content_type.startswith(c) for c in valid_content_types):
        raise AssertionError(
            f"Content-Typeエラー: {content_type} != {valid_content_types}"
        )
    return None


def _create_temp_file(
    tmp_path: pathlib.Path | None, response_body: str
) -> pathlib.Path:
    """一時ファイルを作成してパスを返す。"""
    import pytilpack.pytest_

    tmp_file_path = pytilpack.pytest_.tmp_file_path(tmp_path, suffix=".html")
    tmp_file_path.write_text(response_body, encoding="utf-8")
    logger.info(f"HTML: {tmp_file_path}")
    return tmp_file_path


class ProxyFix:
    """リバースプロキシ対応。

    nginx.conf設定例::
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Forwarded-Prefix $http_x_forwarded_prefix;

    参考: hypercorn.middleware.ProxyFixMiddleware

    """

    def __init__(
        self,
        quartapp: quart.Quart,
        x_for: int = 1,
        x_proto: int = 1,
        x_host: int = 0,
        x_port: int = 0,
        x_prefix: int = 1,
    ):
        self.quartapp = quartapp
        self.asgi_app = quartapp.asgi_app
        self.x_for = x_for
        self.x_proto = x_proto
        self.x_host = x_host
        self.x_port = x_port
        self.x_prefix = x_prefix

    async def __call__(
        self,
        scope: hypercorn.typing.Scope,
        receive: hypercorn.typing.ASGIReceiveCallable,
        send: hypercorn.typing.ASGISendCallable,
    ) -> None:
        if scope["type"] in ("http", "websocket"):
            scope = typing.cast(hypercorn.typing.HTTPScope, copy.deepcopy(scope))
            headers = list(scope["headers"])

            # X-Forwarded-For → client
            forwarded_for = self._get_trusted_value(
                b"x-forwarded-for", headers, self.x_for
            )
            if forwarded_for and scope.get("client"):
                forwarded_for = forwarded_for.split(",")[-1].strip()
                _, orig_port = scope.get("client") or (None, None)
                scope["client"] = (forwarded_for, orig_port or 0)

            # X-Forwarded-Proto → scheme
            forwarded_proto = self._get_trusted_value(
                b"x-forwarded-proto", headers, self.x_proto
            )
            if forwarded_proto:
                scope["scheme"] = forwarded_proto

            # X-Forwarded-Host → server & Host header
            forwarded_host = self._get_trusted_value(
                b"x-forwarded-host", headers, self.x_host
            )
            if forwarded_host:
                host_val = forwarded_host
                host, port = host_val, None
                if ":" in host_val and not host_val.startswith("["):
                    h, p = host_val.rsplit(":", 1)
                    if p.isdigit():
                        host, port = h, int(p)
                # update server tuple
                orig_server = scope.get("server") or (None, None)
                orig_port = orig_server[1]
                scope["server"] = (host, port or orig_port or 0)
                # rebuild Host header
                headers = [(hn, hv) for hn, hv in headers if hn.lower() != b"host"]
                host_hdr = host if port is None else f"{host}:{port}"
                headers.append((b"host", host_hdr.encode("latin1")))

            # X-Forwarded-Port → server port & Host header
            forwarded_port = self._get_trusted_value(
                b"x-forwarded-port", headers, self.x_port
            )
            if forwarded_port and forwarded_port.isdigit():
                port_int = int(forwarded_port)
                orig_server = scope.get("server") or (None, None)
                orig_host = str(orig_server[0])
                scope["server"] = (orig_host, port_int)
                headers = [(hn, hv) for hn, hv in headers if hn.lower() != b"host"]
                headers.append((b"host", f"{orig_host}:{port_int}".encode("latin1")))

            # X-Forwarded-Prefix → root_path + config
            forwarded_prefix = self._get_trusted_value(
                b"x-forwarded-prefix", headers, self.x_prefix
            )
            if forwarded_prefix:
                prefix = forwarded_prefix.rstrip("/")
                scope["root_path"] = scope["root_path"].removeprefix(prefix)
                # config adjustments
                self.quartapp.config["APPLICATION_ROOT"] = prefix
                for key in ("SESSION_COOKIE_PATH", "REMEMBER_COOKIE_PATH"):
                    orig = self.quartapp.config.get(key)
                    if orig:
                        self.quartapp.config[key] = prefix + orig

            scope["headers"] = headers

        await self.asgi_app(scope, receive, send)

    def _get_trusted_value(
        self,
        name: bytes,
        headers: typing.Iterable[tuple[bytes, bytes]],
        trusted_hops: int,
    ) -> str | None:
        if trusted_hops == 0:
            return None

        values = []
        for header_name, header_value in headers:
            if header_name.lower() == name:
                values.extend(
                    [
                        value.decode("latin1").strip()
                        for value in header_value.split(b",")
                    ]
                )

        if len(values) >= trusted_hops:
            return values[-trusted_hops]

        return None
