"""リバースプロキシ対応。"""

import copy
import typing

import hypercorn.typing
import quart
import quart_auth


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
            forwarded_for = self._get_trusted_value(b"x-forwarded-for", headers, self.x_for)
            if forwarded_for and scope.get("client"):
                forwarded_for = forwarded_for.split(",")[-1].strip()
                _, orig_port = scope.get("client") or (None, None)
                scope["client"] = (forwarded_for, orig_port or 0)

            # X-Forwarded-Proto → scheme
            forwarded_proto = self._get_trusted_value(b"x-forwarded-proto", headers, self.x_proto)
            if forwarded_proto:
                scope["scheme"] = forwarded_proto

            # X-Forwarded-Host → server & Host header
            forwarded_host = self._get_trusted_value(b"x-forwarded-host", headers, self.x_host)
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
            forwarded_prefix = self._get_trusted_value(b"x-forwarded-prefix", headers, self.x_prefix)
            if forwarded_prefix and forwarded_prefix != "/":
                prefix = forwarded_prefix.rstrip("/")
                scope["root_path"] = prefix
                self.quartapp.config["APPLICATION_ROOT"] = prefix
                self.quartapp.config["SESSION_COOKIE_PATH"] = prefix
                self.quartapp.config["QUART_AUTH_COOKIE_PATH"] = prefix
                # QuartAuthはinit_app時にコピーしてしまうので強制反映が必要…
                for extension in self.quartapp.extensions.get("QUART_AUTH", []):
                    if isinstance(extension, quart_auth.QuartAuth):
                        extension.cookie_path = prefix

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
