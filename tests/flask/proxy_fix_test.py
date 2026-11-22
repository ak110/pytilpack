import logging
import typing

import flask
import pytest
import werkzeug.test

import pytilpack.flask.proxy_fix


def _noop_start_response(
    status: str, headers: list[tuple[str, str]], exc_info: typing.Any = None
) -> typing.Callable[[bytes], object]:
    del status, headers, exc_info
    return lambda data: None  # type: ignore[return-value]


def _make_app(proxy_fix_kwargs: dict | None = None) -> tuple[flask.Flask, pytilpack.flask.proxy_fix.ProxyFix]:
    app = flask.Flask(__name__)

    @app.route("/test")
    def test_endpoint():
        return "OK"

    kwargs = proxy_fix_kwargs or {}
    middleware = pytilpack.flask.proxy_fix.ProxyFix(app, **kwargs)
    return app, middleware


def _make_environ(
    prefix: str | None = None,
    host: str | None = None,
    path: str = "/test",
) -> dict:
    builder = werkzeug.test.EnvironBuilder(path=path)
    environ = builder.get_environ()
    if prefix:
        environ["HTTP_X_FORWARDED_PREFIX"] = prefix
    if host:
        environ["HTTP_X_FORWARDED_HOST"] = host
    return environ


def test_static_prefix_sets_config_at_init():
    app, _ = _make_app({"static_prefix": "/myapp"})

    assert app.config["APPLICATION_ROOT"] == "/myapp"
    assert app.config["SESSION_COOKIE_PATH"] == "/myapp"
    assert app.config["REMEMBER_COOKIE_PATH"] == "/myapp"


def test_static_prefix_invalid_raises_value_error():
    app = flask.Flask(__name__)

    with pytest.raises(ValueError):
        pytilpack.flask.proxy_fix.ProxyFix(app, static_prefix="//evil.com")

    with pytest.raises(ValueError):
        pytilpack.flask.proxy_fix.ProxyFix(app, static_prefix="noprefix")

    with pytest.raises(ValueError):
        pytilpack.flask.proxy_fix.ProxyFix(app, static_prefix="/bad\x0dprefix")


def test_first_request_pins_prefix():
    app, middleware = _make_app({"x_prefix": 1})

    captured_environ: list[dict] = []

    def capture_app(environ, start_response):
        del start_response
        captured_environ.append(dict(environ))
        return [b"OK"]

    middleware.app = capture_app

    environ = _make_environ(prefix="/app")
    list(middleware(environ, _noop_start_response))

    assert app.config["APPLICATION_ROOT"] == "/app"
    assert app.config["SESSION_COOKIE_PATH"] == "/app"
    assert app.config["REMEMBER_COOKIE_PATH"] == "/app"
    assert captured_environ[0]["SCRIPT_NAME"] == "/app"


def test_pin_does_not_change_on_different_prefix(caplog):
    app, middleware = _make_app({"x_prefix": 1})

    captured_environs: list[dict] = []

    def capture_app(environ, start_response):
        del start_response
        captured_environs.append(dict(environ))
        return [b"OK"]

    middleware.app = capture_app

    environ1 = _make_environ(prefix="/app")
    list(middleware(environ1, _noop_start_response))
    assert app.config["APPLICATION_ROOT"] == "/app"

    with caplog.at_level(logging.WARNING, logger="pytilpack.flask.proxy_fix"):
        environ2 = _make_environ(prefix="/other")
        list(middleware(environ2, _noop_start_response))

    assert app.config["APPLICATION_ROOT"] == "/app"
    assert captured_environs[1]["SCRIPT_NAME"] == "/other"
    assert any("pin済みの値と異なります" in r.message for r in caplog.records)


def test_invalid_prefix_is_rejected(caplog):
    _, middleware = _make_app({"x_prefix": 1})

    captured_environs: list[dict] = []

    def capture_app(environ, start_response):
        del start_response
        captured_environs.append(dict(environ))
        return [b"OK"]

    middleware.app = capture_app

    with caplog.at_level(logging.WARNING, logger="pytilpack.flask.proxy_fix"):
        environ = _make_environ(prefix="//evil.com")
        list(middleware(environ, _noop_start_response))

    assert middleware.flaskapp.config.get("APPLICATION_ROOT", "/") == "/"
    assert captured_environs[0].get("SCRIPT_NAME", "") == ""
    assert any("不正な値" in r.message for r in caplog.records)


def test_crlf_prefix_is_rejected(caplog):
    app, middleware = _make_app({"x_prefix": 1})

    captured_environs: list[dict] = []

    def capture_app(environ, start_response):
        del start_response
        captured_environs.append(dict(environ))
        return [b"OK"]

    middleware.app = capture_app

    with caplog.at_level(logging.WARNING, logger="pytilpack.flask.proxy_fix"):
        environ = _make_environ(prefix="/app\r\nX-Injected: evil")
        list(middleware(environ, _noop_start_response))

    assert app.config.get("APPLICATION_ROOT", "/") == "/"
    assert captured_environs[0].get("SCRIPT_NAME", "") == ""
    assert any("不正な値" in r.message for r in caplog.records)


def test_werkzeug_does_not_reapply_rejected_prefix():
    _, middleware = _make_app({"x_prefix": 1})

    captured_environs: list[dict] = []

    def capture_app(environ, start_response):
        del start_response
        captured_environs.append(dict(environ))
        return [b"OK"]

    middleware.app = capture_app

    environ = _make_environ(prefix="//evil.com")
    list(middleware(environ, _noop_start_response))

    script_name = captured_environs[0].get("SCRIPT_NAME", "")
    assert not script_name.startswith("//")
    assert script_name != "//evil.com"


def test_forwarded_host_trusted_hosts_allowed():
    _, middleware = _make_app({"x_host": 1, "trusted_hosts": ["allowed.example.com"]})

    captured_environs: list[dict] = []

    def capture_app(environ, start_response):
        del start_response
        captured_environs.append(dict(environ))
        return [b"OK"]

    middleware.app = capture_app

    environ = _make_environ(host="allowed.example.com")
    list(middleware(environ, _noop_start_response))

    assert captured_environs[0]["HTTP_HOST"] == "allowed.example.com"


def test_forwarded_host_trusted_hosts_rejected(caplog):
    _, middleware = _make_app({"x_host": 1, "trusted_hosts": ["allowed.example.com"]})

    captured_environs: list[dict] = []

    def capture_app(environ, start_response):
        del start_response
        captured_environs.append(dict(environ))
        return [b"OK"]

    middleware.app = capture_app

    with caplog.at_level(logging.WARNING, logger="pytilpack.flask.proxy_fix"):
        environ = _make_environ(host="evil.example.com")
        list(middleware(environ, _noop_start_response))

    original_host = captured_environs[0].get("HTTP_HOST", "")
    assert "evil.example.com" not in original_host
    assert any("許可リスト外" in r.message for r in caplog.records)


def test_forwarded_host_crlf_rejected(caplog):
    _, middleware = _make_app({"x_host": 1})

    captured_environs: list[dict] = []

    def capture_app(environ, start_response):
        del start_response
        captured_environs.append(dict(environ))
        return [b"OK"]

    middleware.app = capture_app

    with caplog.at_level(logging.WARNING, logger="pytilpack.flask.proxy_fix"):
        environ = _make_environ(host="evil.com\r\nX-Injected: bad")
        list(middleware(environ, _noop_start_response))

    http_host = captured_environs[0].get("HTTP_HOST", "")
    assert "\r" not in http_host
    assert "X-Injected" not in http_host
    assert any("不正な値" in r.message for r in caplog.records)


def test_path_info_prefix_stripped():
    _, middleware = _make_app({"x_prefix": 1})

    captured_environs: list[dict] = []

    def capture_app(environ, start_response):
        del start_response
        captured_environs.append(dict(environ))
        return [b"OK"]

    middleware.app = capture_app

    environ = _make_environ(prefix="/app", path="/app/test")
    list(middleware(environ, _noop_start_response))

    assert captured_environs[0]["SCRIPT_NAME"] == "/app"
    assert captured_environs[0]["PATH_INFO"] == "/test"


@pytest.mark.parametrize(("hops", "expected"), [(0, ""), (1, "/last"), (2, "/app,part"), (3, "/first"), (4, "")])
def test_quoted_prefix_trust_hops(hops: int, expected: str) -> None:
    _, middleware = _make_app({"x_prefix": hops})
    captured: list[dict] = []

    def capture(environ, start_response):
        del start_response
        captured.append(dict(environ))
        return [b"OK"]

    middleware.app = capture
    environ = _make_environ(prefix='/first, "/app,part", /last')
    list(middleware(environ, _noop_start_response))
    assert captured[0]["SCRIPT_NAME"] == expected
