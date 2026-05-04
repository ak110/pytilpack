"""リバースプロキシ対応。"""

import logging
import threading
import typing

import flask
import werkzeug.http
import werkzeug.middleware.proxy_fix

import pytilpack.web

__all__ = ["ProxyFix"]

logger = logging.getLogger(__name__)


class ProxyFix(werkzeug.middleware.proxy_fix.ProxyFix):
    """リバースプロキシ対応。

    nginx.conf設定例::

        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Forwarded-Prefix $http_x_forwarded_prefix;

    設計意図:
        prefixはpin方式で管理する。初回有効リクエスト時に一度だけ``app.config``へ反映し、
        以降は変更しない。これにより攻撃者制御の``X-Forwarded-Prefix``値で
        Cookie発行パス等のアプリ全体設定が書き換わる経路を断つ。

        運用時にprefixが既知であれば、``static_prefix``引数で起動時に確定させることを推奨する。
        ``static_prefix``を指定した場合、初期化時に``app.config``を確定する。
        ただし``environ["SCRIPT_NAME"]``はリクエストごとに``X-Forwarded-Prefix``ヘッダーの値から
        設定するため、ヘッダーが来ないリクエストでは``environ["SCRIPT_NAME"]``は更新されない。

        ``x_host > 0``でX-Forwarded-Hostを有効化する場合は、``trusted_hosts``引数で
        許可ホストリストを指定することを推奨する。指定がない場合は値検証（制御文字・
        ``//``始まり等の排除）のみ行い追加警告は出さない。

        ``x_prefix``と``x_host``はpytilpack側で完全管理し、親クラスへは``x_prefix=0``・
        ``x_host=0``を渡す。これにより検証で弾いた値が親クラス側で再反映される経路を断つ。

        旧挙動（リクエストごとに``app.config``を上書き）を期待していた利用者は、
        ``static_prefix``指定方式、またはpin後の挙動（初回リクエストでpinされる）へ移行すること。

    """

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
        # x_prefix・x_hostは自前処理するため親クラスへは無効化して渡す
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

        self._pin_lock = threading.Lock()
        self._pinned_prefix: str | None = None
        self._prefix_pinned = False

        if static_prefix is not None:
            validated = pytilpack.web.validate_forwarded_prefix(static_prefix)
            if validated is None:
                raise ValueError(f"static_prefixが不正: {static_prefix!r}")
            self._apply_prefix_to_config(validated)
            self._pinned_prefix = validated
            self._prefix_pinned = True

    def _apply_prefix_to_config(self, prefix: str) -> None:
        """prefixをapp.configへ反映する。"""
        self.flaskapp.config["APPLICATION_ROOT"] = prefix
        self.flaskapp.config["SESSION_COOKIE_PATH"] = prefix
        self.flaskapp.config["REMEMBER_COOKIE_PATH"] = prefix

    def _get_header_value(self, environ: dict, header_key: str, trusted_hops: int) -> str | None:
        """WSGIのenvironからカンマ区切りヘッダーの信頼ホップ位置の値を取得する。

        quoted-string対応のカンマ分割にwerkzeug.http.parse_list_headerを使い、
        werkzeug標準の_get_real_valueと同等の処理を行う。
        _get_real_valueは内部APIであるため、自前で実装してバージョン互換性を確保する。
        """
        if trusted_hops == 0:
            return None
        value = environ.get(header_key)
        if not value:
            return None
        values = werkzeug.http.parse_list_header(value)
        if len(values) >= trusted_hops:
            return values[-trusted_hops]
        return None

    @typing.override
    def __call__(self, environ, start_response):
        # X-Forwarded-Host処理（自前）
        if self._x_host != 0:
            x_host = self._get_header_value(environ, "HTTP_X_FORWARDED_HOST", self._x_host)
            if x_host:
                validated_host = pytilpack.web.validate_forwarded_host(x_host)
                if validated_host is None:
                    logger.warning(f"X-Forwarded-Hostに不正な値が含まれています: {x_host!r}")
                elif self.trusted_hosts is not None and not pytilpack.web.is_host_in_trusted(
                    validated_host, self.trusted_hosts
                ):
                    logger.warning(f"X-Forwarded-Hostが許可リスト外です: {validated_host!r}")
                else:
                    environ["HTTP_HOST"] = validated_host

        # X-Forwarded-Prefix処理（自前）
        if self._x_prefix != 0:
            x_prefix = self._get_header_value(environ, "HTTP_X_FORWARDED_PREFIX", self._x_prefix)
            if x_prefix:
                prefix = pytilpack.web.validate_forwarded_prefix(x_prefix)
                if prefix is None:
                    logger.warning(f"X-Forwarded-Prefixに不正な値が含まれています: {x_prefix!r}")
                else:
                    environ["SCRIPT_NAME"] = prefix
                    path_info = environ.get("PATH_INFO", "")
                    if path_info.startswith(prefix):
                        environ["PATH_INFO"] = path_info[len(prefix) :]
                    if not self._prefix_pinned:
                        with self._pin_lock:
                            if not self._prefix_pinned:
                                self._apply_prefix_to_config(prefix)
                                self._pinned_prefix = prefix
                                self._prefix_pinned = True
                            elif self._pinned_prefix != prefix:
                                logger.warning(
                                    f"X-Forwarded-Prefixがpin済みの値と異なります: "
                                    f"pinned={self._pinned_prefix!r}, received={prefix!r}"
                                )
                    elif self._pinned_prefix != prefix:
                        logger.warning(
                            f"X-Forwarded-Prefixがpin済みの値と異なります: pinned={self._pinned_prefix!r}, received={prefix!r}"
                        )

        return super().__call__(environ, start_response)
