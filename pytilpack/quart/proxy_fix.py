"""リバースプロキシ対応。"""

import copy
import logging
import typing

import hypercorn.typing
import quart
import quart_auth

import pytilpack.web

__all__ = ["ProxyFix"]

logger = logging.getLogger(__name__)


class ProxyFix:
    """リバースプロキシ対応。

    nginx.conf設定例::

        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Forwarded-Prefix $http_x_forwarded_prefix;

    参考:
        - hypercorn.middleware.ProxyFixMiddleware
          <https://github.com/pgjones/hypercorn/blob/main/src/hypercorn/middleware/proxy_fix.py>

    設計意図:
        prefixはpin方式で管理する。初回有効リクエスト時に一度だけ``app.config``へ反映し、
        以降は変更しない。これにより攻撃者制御の``X-Forwarded-Prefix``値で
        Cookie発行パス等のアプリ全体設定が書き換わる経路を断つ。

        運用時にprefixが既知であれば、``static_prefix``引数で起動時に確定させることを推奨する。
        ``static_prefix``を指定した場合、初期化時に``app.config``を確定する。
        ただし``scope["root_path"]``はリクエストごとに``X-Forwarded-Prefix``ヘッダーの値から
        設定するため、ヘッダーが来ないリクエストでは``scope["root_path"]``は更新されない。

        ``x_host > 0``でX-Forwarded-Hostを有効化する場合は、``trusted_hosts``引数で
        許可ホストリストを指定することを推奨する。指定がない場合は値検証（制御文字・
        ``//``始まり等の排除）のみ行い追加警告は出力しない。

        旧挙動（リクエストごとに``app.config``を上書き）を期待していた利用者は、
        ``static_prefix``指定方式、またはpin後の挙動（初回リクエストでpinされる）へ移行すること。

    """

    def __init__(
        self,
        quartapp: quart.Quart,
        x_for: int = 1,
        x_proto: int = 1,
        x_host: int = 0,
        x_port: int = 0,
        x_prefix: int = 1,
        static_prefix: str | None = None,
        trusted_hosts: typing.Iterable[str] | None = None,
    ):
        self.quartapp = quartapp
        self.asgi_app = quartapp.asgi_app
        self.x_for = x_for
        self.x_proto = x_proto
        self.x_port = x_port
        self._x_host = x_host
        self._x_prefix = x_prefix
        self.trusted_hosts = list(trusted_hosts) if trusted_hosts is not None else None

        self._pin = pytilpack.web.PrefixPinner(apply=self._apply_prefix_to_config, warn=logger.warning)
        self._pin.initialize(static_prefix)

    def _apply_prefix_to_config(self, prefix: str) -> None:
        """prefixをapp.configおよびQuartAuthインスタンスへ反映する。"""
        self.quartapp.config["APPLICATION_ROOT"] = prefix
        self.quartapp.config["SESSION_COOKIE_PATH"] = prefix
        self.quartapp.config["QUART_AUTH_COOKIE_PATH"] = prefix
        # QuartAuthはinit_app時にコピーしてしまうので強制反映が必要
        for extension in self.quartapp.extensions.get("QUART_AUTH", []):
            if isinstance(extension, quart_auth.QuartAuth):
                extension.cookie_path = prefix

    async def __call__(
        self,
        scope: hypercorn.typing.Scope,
        receive: hypercorn.typing.ASGIReceiveCallable,
        send: hypercorn.typing.ASGISendCallable,
    ) -> None:
        """ASGIアプリケーションとしての処理。"""
        if scope["type"] in ("http", "websocket"):
            scope = typing.cast(hypercorn.typing.HTTPScope, copy.deepcopy(scope))
            headers = list(scope["headers"])

            # X-Forwarded-For → client
            forwarded_for = self._get_trusted_value(b"x-forwarded-for", headers, self.x_for)
            if forwarded_for and scope.get("client"):
                _, orig_port = scope.get("client") or (None, None)
                scope["client"] = (forwarded_for, orig_port or 0)

            # X-Forwarded-Proto → scheme
            forwarded_proto = self._get_trusted_value(b"x-forwarded-proto", headers, self.x_proto)
            if forwarded_proto:
                scope["scheme"] = forwarded_proto

            # X-Forwarded-Host → server & Host header
            forwarded_host = self._get_trusted_value(b"x-forwarded-host", headers, self._x_host)
            if forwarded_host:
                validated_host = pytilpack.web.validate_forwarded_host(forwarded_host)
                if validated_host is None:
                    logger.warning(f"X-Forwarded-Hostに不正な値が含まれています: {forwarded_host!r}")
                elif self.trusted_hosts is not None and not pytilpack.web.is_host_in_trusted(
                    validated_host, self.trusted_hosts
                ):
                    logger.warning(f"X-Forwarded-Hostが許可リスト外です: {validated_host!r}")
                else:
                    host_val = validated_host
                    host, port = host_val, None
                    if ":" in host_val and not host_val.startswith("["):
                        h, p = host_val.rsplit(":", 1)
                        if p.isdigit():
                            host, port = h, int(p)
                    orig_server = scope.get("server") or (None, None)
                    orig_port = orig_server[1]
                    scope["server"] = (host, port or orig_port or 0)
                    headers = [(hn, hv) for hn, hv in headers if hn.lower() != b"host"]
                    host_hdr = host if port is None else f"{host}:{port}"
                    headers.append((b"host", host_hdr.encode("utf-8", errors="replace")))

            # X-Forwarded-Port → server port & Host header
            forwarded_port = self._get_trusted_value(b"x-forwarded-port", headers, self.x_port)
            if forwarded_port and forwarded_port.isdigit():
                port_int = int(forwarded_port)
                orig_server = scope.get("server") or (None, None)
                orig_host = str(orig_server[0])
                scope["server"] = (orig_host, port_int)
                headers = [(hn, hv) for hn, hv in headers if hn.lower() != b"host"]
                headers.append((b"host", f"{orig_host}:{port_int}".encode()))

            # X-Forwarded-Prefix → root_path + config
            forwarded_prefix = self._get_trusted_value(b"x-forwarded-prefix", headers, self._x_prefix)
            if forwarded_prefix:
                prefix = pytilpack.web.validate_forwarded_prefix(forwarded_prefix)
                if prefix is None:
                    logger.warning(f"X-Forwarded-Prefixに不正な値が含まれています: {forwarded_prefix!r}")
                else:
                    scope["root_path"] = prefix
                    self._pin.pin(prefix)

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
                values.extend([value.decode("utf-8", errors="replace").strip() for value in header_value.split(b",")])

        if len(values) >= trusted_hops:
            return values[-trusted_hops]

        return None
