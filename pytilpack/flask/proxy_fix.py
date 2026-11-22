__lazy_modules__ = ["flask", "logging", "pytilpack.web", "typing", "werkzeug.middleware.proxy_fix"]

import logging
import typing

import flask
import werkzeug.middleware.proxy_fix

import pytilpack.web

__all__ = ["ProxyFix"]

logger = logging.getLogger(__name__)


class ProxyFix(werkzeug.middleware.proxy_fix.ProxyFix):
    def __init__(
        self,
        flaskapp: flask.Flask,
        x_for: int = 1,
        x_proto: int = 1,
        x_host: int = 0,
        x_port: int = 0,
        x_prefix: int = 1,
        static_prefix: str | None = None,
        trusted_hosts: typing.Iterable[str] | None = None,
    ):
        super().__init__(
            flaskapp.wsgi_app,
            x_for=x_for,
            x_proto=x_proto,
            x_host=0,
            x_port=x_port,
            x_prefix=0,
        )
        self.flaskapp = flaskapp
        self._x_prefix = x_prefix
        self._x_host = x_host
        self.trusted_hosts = list(trusted_hosts) if trusted_hosts is not None else None

        self._pin = pytilpack.web.PrefixPinner(apply=self._apply_prefix_to_config, warn=logger.warning)
        self._pin.initialize(static_prefix)

    def _apply_prefix_to_config(self, prefix: str) -> None:
        self.flaskapp.config["APPLICATION_ROOT"] = prefix
        self.flaskapp.config["SESSION_COOKIE_PATH"] = prefix
        self.flaskapp.config["REMEMBER_COOKIE_PATH"] = prefix

    def _get_header_value(self, environ: dict, header_key: str, trusted_hops: int) -> str | None:
        value = environ.get(header_key)
        return pytilpack.web.get_trusted_header_value([value] if value else [], trusted_hops)

    @typing.override
    def __call__(self, environ, start_response):
        if self._x_host != 0:
            x_host = self._get_header_value(environ, "HTTP_X_FORWARDED_HOST", self._x_host)
            if x_host:
                validated_host = pytilpack.web.validate_forwarded_host(x_host)
                if validated_host is None:
                    logger.warning(
                        f"X-Forwarded-Hostに不正な値が含まれています: {x_host!r}。"
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
                    environ["HTTP_HOST"] = validated_host

        if self._x_prefix != 0:
            x_prefix = self._get_header_value(environ, "HTTP_X_FORWARDED_PREFIX", self._x_prefix)
            if x_prefix:
                prefix = pytilpack.web.validate_forwarded_prefix(x_prefix)
                if prefix is None:
                    logger.warning(
                        f"X-Forwarded-Prefixに不正な値が含まれています: {x_prefix!r}。"
                        "このヘッダーを無視して処理を続ける。プロキシが送るX-Forwarded-Prefixの設定を見直す"
                    )
                else:
                    environ["SCRIPT_NAME"] = prefix
                    path_info = environ.get("PATH_INFO", "")
                    if path_info.startswith(prefix):
                        environ["PATH_INFO"] = path_info[len(prefix) :]
                    self._pin.pin(prefix)

        return super().__call__(environ, start_response)
