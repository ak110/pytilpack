import asyncio
import logging
import typing

import pytest
import quart
import quart_auth

import pytilpack.quart.proxy_fix

_DummyReceive = typing.Callable[[], typing.Awaitable[typing.Any]]
_DummySend = typing.Callable[[typing.Any], typing.Awaitable[None]]


async def _noop_receive() -> typing.Any:
    await asyncio.sleep(0)
    return {}


async def _noop_send(msg: typing.Any) -> None:
    del msg


def _make_app(proxy_fix_kwargs: dict | None = None) -> tuple[quart.Quart, pytilpack.quart.proxy_fix.ProxyFix]:
    app = quart.Quart(__name__)

    @app.route("/test")
    async def test_endpoint():
        return "OK"

    kwargs = proxy_fix_kwargs or {}
    middleware = pytilpack.quart.proxy_fix.ProxyFix(app, **kwargs)
    return app, middleware


def _make_scope(headers: list[tuple[bytes, bytes]] | None = None) -> dict:
    return {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "root_path": "",
        "query_string": b"",
        "headers": headers or [],
        "server": ("localhost", 80),
        "client": ("127.0.0.1", 12345),
        "scheme": "http",
    }


@pytest.mark.asyncio
async def test_static_prefix_sets_config_at_init():
    app, _ = _make_app({"static_prefix": "/myapp"})

    assert app.config["APPLICATION_ROOT"] == "/myapp"
    assert app.config["SESSION_COOKIE_PATH"] == "/myapp"
    assert app.config["QUART_AUTH_COOKIE_PATH"] == "/myapp"


@pytest.mark.asyncio
async def test_static_prefix_sets_quart_auth_cookie_path():
    app = quart.Quart(__name__)

    @app.route("/test")
    async def test_endpoint():
        return "OK"

    quart_auth_ext = quart_auth.QuartAuth(app)
    pytilpack.quart.proxy_fix.ProxyFix(app, static_prefix="/myapp")

    assert quart_auth_ext.cookie_path == "/myapp"


@pytest.mark.asyncio
async def test_static_prefix_invalid_raises_value_error():
    app = quart.Quart(__name__)

    with pytest.raises(ValueError):
        pytilpack.quart.proxy_fix.ProxyFix(app, static_prefix="//evil.com")

    with pytest.raises(ValueError):
        pytilpack.quart.proxy_fix.ProxyFix(app, static_prefix="noprefix")

    with pytest.raises(ValueError):
        pytilpack.quart.proxy_fix.ProxyFix(app, static_prefix="/bad\x0dprefix")


@pytest.mark.asyncio
async def test_first_request_pins_prefix():
    app, middleware = _make_app({"x_prefix": 1})

    received_scopes: list[dict] = []

    async def fake_asgi(scope: typing.Any, receive: typing.Any, send: typing.Any) -> None:
        del receive, send
        received_scopes.append(scope)

    middleware.asgi_app = fake_asgi

    scope = _make_scope([(b"x-forwarded-prefix", b"/app")])
    await middleware(scope, _noop_receive, _noop_send)  # type: ignore[arg-type]

    assert app.config["APPLICATION_ROOT"] == "/app"
    assert app.config["SESSION_COOKIE_PATH"] == "/app"
    assert app.config["QUART_AUTH_COOKIE_PATH"] == "/app"
    assert received_scopes[0]["root_path"] == "/app"


@pytest.mark.asyncio
async def test_pin_does_not_change_on_different_prefix(caplog):
    app, middleware = _make_app({"x_prefix": 1})

    received_scopes: list[dict] = []

    async def fake_asgi(scope: typing.Any, receive: typing.Any, send: typing.Any) -> None:
        del receive, send
        received_scopes.append(scope)

    middleware.asgi_app = fake_asgi

    scope1 = _make_scope([(b"x-forwarded-prefix", b"/app")])
    await middleware(scope1, _noop_receive, _noop_send)  # type: ignore[arg-type]
    assert app.config["APPLICATION_ROOT"] == "/app"

    with caplog.at_level(logging.WARNING, logger="pytilpack.quart.proxy_fix"):
        scope2 = _make_scope([(b"x-forwarded-prefix", b"/other")])
        await middleware(scope2, _noop_receive, _noop_send)  # type: ignore[arg-type]

    assert app.config["APPLICATION_ROOT"] == "/app"
    assert received_scopes[1]["root_path"] == "/other"
    assert any("pin済みの値と異なります" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_invalid_prefix_is_rejected(caplog):
    _, middleware = _make_app({"x_prefix": 1})

    received_scopes: list[dict] = []

    async def fake_asgi(scope: typing.Any, receive: typing.Any, send: typing.Any) -> None:
        del receive, send
        received_scopes.append(scope)

    middleware.asgi_app = fake_asgi

    with caplog.at_level(logging.WARNING, logger="pytilpack.quart.proxy_fix"):
        scope = _make_scope([(b"x-forwarded-prefix", b"//evil.com")])
        await middleware(scope, _noop_receive, _noop_send)  # type: ignore[arg-type]

    assert middleware.quartapp.config.get("APPLICATION_ROOT", "/") == "/"
    assert received_scopes[0].get("root_path", "") == ""
    assert any("不正な値" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_crlf_prefix_is_rejected(caplog):
    app, middleware = _make_app({"x_prefix": 1})

    received_scopes: list[dict] = []

    async def fake_asgi(scope: typing.Any, receive: typing.Any, send: typing.Any) -> None:
        del receive, send
        received_scopes.append(scope)

    middleware.asgi_app = fake_asgi

    with caplog.at_level(logging.WARNING, logger="pytilpack.quart.proxy_fix"):
        scope = _make_scope([(b"x-forwarded-prefix", b"/app\r\nX-Injected: evil")])
        await middleware(scope, _noop_receive, _noop_send)  # type: ignore[arg-type]

    assert app.config.get("APPLICATION_ROOT", "/") == "/"
    assert received_scopes[0].get("root_path", "") == ""
    assert any("不正な値" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_forwarded_host_trusted_hosts_allowed():
    _, middleware = _make_app({"x_host": 1, "trusted_hosts": ["allowed.example.com"]})

    received_scopes: list[dict] = []

    async def fake_asgi(scope: typing.Any, receive: typing.Any, send: typing.Any) -> None:
        del receive, send
        received_scopes.append(scope)

    middleware.asgi_app = fake_asgi

    scope = _make_scope([(b"host", b"localhost"), (b"x-forwarded-host", b"allowed.example.com")])
    await middleware(scope, _noop_receive, _noop_send)  # type: ignore[arg-type]

    assert received_scopes[0]["server"] == ("allowed.example.com", 80)
    assert [value for name, value in received_scopes[0]["headers"] if name == b"host"] == [b"allowed.example.com"]


@pytest.mark.asyncio
async def test_forwarded_host_trusted_hosts_rejected(caplog):
    _, middleware = _make_app({"x_host": 1, "trusted_hosts": ["allowed.example.com"]})

    received_scopes: list[dict] = []

    async def fake_asgi(scope: typing.Any, receive: typing.Any, send: typing.Any) -> None:
        del receive, send
        received_scopes.append(scope)

    middleware.asgi_app = fake_asgi

    with caplog.at_level(logging.WARNING, logger="pytilpack.quart.proxy_fix"):
        scope = _make_scope([(b"host", b"localhost"), (b"x-forwarded-host", b"evil.example.com")])
        await middleware(scope, _noop_receive, _noop_send)  # type: ignore[arg-type]

    assert received_scopes[0]["server"] == ("localhost", 80)
    assert [value for name, value in received_scopes[0]["headers"] if name == b"host"] == [b"localhost"]
    assert any("許可リスト外" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_forwarded_host_crlf_rejected(caplog):
    _, middleware = _make_app({"x_host": 1})

    received_scopes: list[dict] = []

    async def fake_asgi(scope: typing.Any, receive: typing.Any, send: typing.Any) -> None:
        del receive, send
        received_scopes.append(scope)

    middleware.asgi_app = fake_asgi

    with caplog.at_level(logging.WARNING, logger="pytilpack.quart.proxy_fix"):
        scope = _make_scope([(b"host", b"localhost"), (b"x-forwarded-host", b"evil.com\r\nX-Injected: bad")])
        await middleware(scope, _noop_receive, _noop_send)  # type: ignore[arg-type]

    assert received_scopes[0]["server"] == ("localhost", 80)
    assert [value for name, value in received_scopes[0]["headers"] if name == b"host"] == [b"localhost"]
    assert any("不正な値" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_static_prefix_scope_root_path_is_set():
    app, middleware = _make_app({"static_prefix": "/myapp", "x_prefix": 1})
    assert app.config["APPLICATION_ROOT"] == "/myapp"

    received_scopes: list[dict] = []

    async def fake_asgi(scope: typing.Any, receive: typing.Any, send: typing.Any) -> None:
        del receive, send
        received_scopes.append(scope)

    middleware.asgi_app = fake_asgi

    scope = _make_scope([(b"x-forwarded-prefix", b"/other")])
    await middleware(scope, _noop_receive, _noop_send)  # type: ignore[arg-type]

    assert received_scopes[0]["root_path"] == "/other"
    assert app.config["APPLICATION_ROOT"] == "/myapp"


@pytest.mark.asyncio
@pytest.mark.parametrize(("hops", "expected"), [(0, ""), (1, "/last"), (2, "/app,part"), (3, "/first"), (4, "")])
async def test_quoted_prefix_across_header_lines(hops: int, expected: str) -> None:
    _, middleware = _make_app({"x_prefix": hops})
    captured: list[dict] = []

    async def capture(scope: typing.Any, receive: typing.Any, send: typing.Any) -> None:
        del receive, send
        captured.append(scope)

    middleware.asgi_app = capture
    scope = _make_scope([(b"x-forwarded-prefix", b"/first"), (b"x-forwarded-prefix", b'"/app,part", /last')])
    await middleware(scope, _noop_receive, _noop_send)  # type: ignore[arg-type]
    assert captured[0]["root_path"] == expected
