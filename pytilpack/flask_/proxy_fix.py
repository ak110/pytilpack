"""リバースプロキシ対応。"""

import typing

import flask
import werkzeug.middleware.proxy_fix


class ProxyFix(werkzeug.middleware.proxy_fix.ProxyFix):
    """リバースプロキシ対応。

    nginx.conf設定例::
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Forwarded-Prefix $http_x_forwarded_prefix;

    """

    def __init__(
        self,
        flaskapp: flask.Flask,
        x_for: int = 1,
        x_proto: int = 1,
        x_host: int = 0,
        x_port: int = 0,
        x_prefix: int = 1,
    ):
        super().__init__(
            flaskapp.wsgi_app,
            x_for=x_for,
            x_proto=x_proto,
            x_host=x_host,
            x_port=x_port,
            x_prefix=x_prefix,
        )
        self.flaskapp = flaskapp

    @typing.override
    def __call__(self, environ, start_response):
        if self.x_prefix != 0:
            prefix = environ.get("HTTP_X_FORWARDED_PREFIX", "/")
            if prefix != "/":
                environ["SCRIPT_NAME"] = prefix
                environ["PATH_INFO"] = environ["PATH_INFO"][len(prefix) :]
                self.flaskapp.config["APPLICATION_ROOT"] = prefix
                self.flaskapp.config["SESSION_COOKIE_PATH"] = prefix
                self.flaskapp.config["REMEMBER_COOKIE_PATH"] = prefix
        return super().__call__(environ, start_response)
