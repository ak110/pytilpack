__lazy_modules__ = ["copy", "hypercorn.typing", "logging", "pytilpack.web", "quart", "quart_auth", "typing"]

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
        self.quartapp.config["APPLICATION_ROOT"] = prefix
        self.quartapp.config["SESSION_COOKIE_PATH"] = prefix
        self.quartapp.config["QUART_AUTH_COOKIE_PATH"] = prefix
        for extension in self.quartapp.extensions.get("QUART_AUTH", []):
            if isinstance(extension, quart_auth.QuartAuth):
                extension.cookie_path = prefix

    async def __call__(
        self,
        scope: hypercorn.typing.Scope,
        receive: hypercorn.typing.ASGIReceiveCallable,
        send: hypercorn.typing.ASGISendCallable,
    ) -> None:
        if scope["type"] in ("http", "websocket"):
            scope = typing.cast(hypercorn.typing.HTTPScope, copy.deepcopy(scope))
            headers = list(scope["headers"])

            forwarded_for = self._get_trusted_value(b"x-forwarded-for", headers, self.x_for)
            if forwarded_for and scope.get("client"):
                _, orig_port = scope.get("client") or (None, None)
                scope["client"] = (forwarded_for, orig_port or 0)

            forwarded_proto = self._get_trusted_value(b"x-forwarded-proto", headers, self.x_proto)
            if forwarded_proto:
                scope["scheme"] = forwarded_proto

            forwarded_host = self._get_trusted_value(b"x-forwarded-host", headers, self._x_host)
            if forwarded_host:
                validated_host = pytilpack.web.validate_forwarded_host(forwarded_host)
                if validated_host is None:
                    logger.warning(
                        f"X-Forwarded-Hostに不正な値が含まれています: {forwarded_host!r}。"
                        "このヘッダーを無視して処理を続ける。プロキシが送るX-Forwarded-Hostの設定を見直す"
                    )
                elif self.trusted_hosts is not None and not pytilpack.web.is_host_in_trusted(
                    validated_host, self.trusted_hosts
                ):
                    logger.warning(
                        f"X-Forwarded-Hostが許可リスト外です: {validated_host!r}。"
                        "このヘッダーを無視して処理を続ける。正当なホストならProxyFixのtrusted_hostsへ追加する"
                    )
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

            forwarded_port = self._get_trusted_value(b"x-forwarded-port", headers, self.x_port)
            if forwarded_port and forwarded_port.isdigit():
                port_int = int(forwarded_port)
                orig_server = scope.get("server") or (None, None)
                orig_host = str(orig_server[0])
                scope["server"] = (orig_host, port_int)
                headers = [(hn, hv) for hn, hv in headers if hn.lower() != b"host"]
                headers.append((b"host", f"{orig_host}:{port_int}".encode()))

            forwarded_prefix = self._get_trusted_value(b"x-forwarded-prefix", headers, self._x_prefix)
            if forwarded_prefix:
                prefix = pytilpack.web.validate_forwarded_prefix(forwarded_prefix)
                if prefix is None:
                    logger.warning(
                        f"X-Forwarded-Prefixに不正な値が含まれています: {forwarded_prefix!r}。"
                        "このヘッダーを無視して処理を続ける。プロキシが送るX-Forwarded-Prefixの設定を見直す"
                    )
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
        return pytilpack.web.get_trusted_header_value(
            (value.decode("utf-8", errors="replace") for header_name, value in headers if header_name.lower() == name),
            trusted_hops,
        )
