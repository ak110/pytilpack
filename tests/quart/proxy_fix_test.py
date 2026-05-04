"""Quart ProxyFixのテスト。"""

import asyncio
import logging
import typing

import pytest
import quart
import quart_auth

import pytilpack.quart.proxy_fix

# ASGIのreceive/sendのダミー型
_DummyReceive = typing.Callable[[], typing.Awaitable[typing.Any]]
_DummySend = typing.Callable[[typing.Any], typing.Awaitable[None]]


async def _noop_receive() -> typing.Any:
    """ダミーのASGI receive。"""
    await asyncio.sleep(0)
    return {}


async def _noop_send(msg: typing.Any) -> None:
    """ダミーのASGI send。"""
    del msg


def _make_app(proxy_fix_kwargs: dict | None = None) -> tuple[quart.Quart, pytilpack.quart.proxy_fix.ProxyFix]:
    """テスト用Quartアプリとプロキシミドルウェアを生成する。"""
    app = quart.Quart(__name__)

    @app.route("/test")
    async def test_endpoint():
        return "OK"

    kwargs = proxy_fix_kwargs or {}
    middleware = pytilpack.quart.proxy_fix.ProxyFix(app, **kwargs)
    return app, middleware


def _make_scope(headers: list[tuple[bytes, bytes]] | None = None) -> dict:
    """テスト用ASGIスコープを生成する。"""
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
    """static_prefix指定時に初期化でapp.configが確定することのテスト。"""
    app, _ = _make_app({"static_prefix": "/myapp"})

    assert app.config["APPLICATION_ROOT"] == "/myapp"
    assert app.config["SESSION_COOKIE_PATH"] == "/myapp"
    assert app.config["QUART_AUTH_COOKIE_PATH"] == "/myapp"


@pytest.mark.asyncio
async def test_static_prefix_sets_quart_auth_cookie_path():
    """static_prefix指定時にQuartAuthのcookie_pathが確定することのテスト。"""
    app = quart.Quart(__name__)

    @app.route("/test")
    async def test_endpoint():
        return "OK"

    quart_auth_ext = quart_auth.QuartAuth(app)
    pytilpack.quart.proxy_fix.ProxyFix(app, static_prefix="/myapp")

    assert quart_auth_ext.cookie_path == "/myapp"


@pytest.mark.asyncio
async def test_static_prefix_invalid_raises_value_error():
    """static_prefixに不正な値を指定するとValueErrorが送出されることのテスト。"""
    app = quart.Quart(__name__)

    with pytest.raises(ValueError):
        pytilpack.quart.proxy_fix.ProxyFix(app, static_prefix="//evil.com")

    with pytest.raises(ValueError):
        pytilpack.quart.proxy_fix.ProxyFix(app, static_prefix="noprefix")

    with pytest.raises(ValueError):
        pytilpack.quart.proxy_fix.ProxyFix(app, static_prefix="/bad\x0dprefix")


@pytest.mark.asyncio
async def test_first_request_pins_prefix():
    """初回リクエストでprefixがpinされることのテスト。"""
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
async def test_pin_does_not_change_on_second_request_with_same_prefix():
    """pin後に同じprefixを受信してもapp.configが変わらないことのテスト。"""
    app, middleware = _make_app({"x_prefix": 1})

    async def fake_asgi(scope: typing.Any, receive: typing.Any, send: typing.Any) -> None:
        del scope, receive, send

    middleware.asgi_app = fake_asgi

    scope1 = _make_scope([(b"x-forwarded-prefix", b"/app")])
    await middleware(scope1, _noop_receive, _noop_send)  # type: ignore[arg-type]
    assert app.config["APPLICATION_ROOT"] == "/app"

    # 2回目も同じ値
    scope2 = _make_scope([(b"x-forwarded-prefix", b"/app")])
    await middleware(scope2, _noop_receive, _noop_send)  # type: ignore[arg-type]
    assert app.config["APPLICATION_ROOT"] == "/app"


@pytest.mark.asyncio
async def test_pin_does_not_change_on_different_prefix(caplog):
    """pin後に異なるprefixを受信してもapp.configが変わらず、scopeだけ書き換わることのテスト。"""
    app, middleware = _make_app({"x_prefix": 1})

    received_scopes: list[dict] = []

    async def fake_asgi(scope: typing.Any, receive: typing.Any, send: typing.Any) -> None:
        del receive, send
        received_scopes.append(scope)

    middleware.asgi_app = fake_asgi

    scope1 = _make_scope([(b"x-forwarded-prefix", b"/app")])
    await middleware(scope1, _noop_receive, _noop_send)  # type: ignore[arg-type]
    assert app.config["APPLICATION_ROOT"] == "/app"

    # pin後に異なる値
    with caplog.at_level(logging.WARNING, logger="pytilpack.quart.proxy_fix"):
        scope2 = _make_scope([(b"x-forwarded-prefix", b"/other")])
        await middleware(scope2, _noop_receive, _noop_send)  # type: ignore[arg-type]

    # app.configは変わらない
    assert app.config["APPLICATION_ROOT"] == "/app"
    # scopeは書き換わる
    assert received_scopes[1]["root_path"] == "/other"
    # 警告が出る
    assert any("pin済みの値と異なります" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_invalid_prefix_is_rejected(caplog):
    """不正なprefixが拒否されapp.configが変わらないことのテスト。"""
    _, middleware = _make_app({"x_prefix": 1})

    received_scopes: list[dict] = []

    async def fake_asgi(scope: typing.Any, receive: typing.Any, send: typing.Any) -> None:
        del receive, send
        received_scopes.append(scope)

    middleware.asgi_app = fake_asgi

    # //evil.com を送る
    with caplog.at_level(logging.WARNING, logger="pytilpack.quart.proxy_fix"):
        scope = _make_scope([(b"x-forwarded-prefix", b"//evil.com")])
        await middleware(scope, _noop_receive, _noop_send)  # type: ignore[arg-type]

    # app.configは変わらない（初回でも）
    assert middleware.quartapp.config.get("APPLICATION_ROOT", "/") == "/"
    assert not middleware._prefix_pinned  # pylint: disable=protected-access
    # scopeのroot_pathも変わらない
    assert received_scopes[0].get("root_path", "") == ""
    # 警告が出る
    assert any("不正な値" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_crlf_prefix_is_rejected(caplog):
    """CRLF混入prefixが拒否されることのテスト。"""
    _, middleware = _make_app({"x_prefix": 1})

    async def fake_asgi(scope: typing.Any, receive: typing.Any, send: typing.Any) -> None:
        del scope, receive, send

    middleware.asgi_app = fake_asgi

    with caplog.at_level(logging.WARNING, logger="pytilpack.quart.proxy_fix"):
        scope = _make_scope([(b"x-forwarded-prefix", b"/app\r\nX-Injected: evil")])
        await middleware(scope, _noop_receive, _noop_send)  # type: ignore[arg-type]

    assert not middleware._prefix_pinned  # pylint: disable=protected-access
    assert any("不正な値" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_forwarded_host_trusted_hosts_allowed():
    """trusted_hostsに含まれるホストがX-Forwarded-Hostとして反映されることのテスト。"""
    _, middleware = _make_app({"x_host": 1, "trusted_hosts": ["allowed.example.com"]})

    received_scopes: list[dict] = []

    async def fake_asgi(scope: typing.Any, receive: typing.Any, send: typing.Any) -> None:
        del receive, send
        received_scopes.append(scope)

    middleware.asgi_app = fake_asgi

    scope = _make_scope([(b"x-forwarded-host", b"allowed.example.com")])
    await middleware(scope, _noop_receive, _noop_send)  # type: ignore[arg-type]

    # scopeのserverが更新されている
    assert received_scopes[0]["server"][0] == "allowed.example.com"


@pytest.mark.asyncio
async def test_forwarded_host_trusted_hosts_rejected(caplog):
    """trusted_hostsに含まれないホストが反映されないことのテスト。"""
    _, middleware = _make_app({"x_host": 1, "trusted_hosts": ["allowed.example.com"]})

    received_scopes: list[dict] = []

    async def fake_asgi(scope: typing.Any, receive: typing.Any, send: typing.Any) -> None:
        del receive, send
        received_scopes.append(scope)

    middleware.asgi_app = fake_asgi

    with caplog.at_level(logging.WARNING, logger="pytilpack.quart.proxy_fix"):
        scope = _make_scope([(b"x-forwarded-host", b"evil.example.com")])
        await middleware(scope, _noop_receive, _noop_send)  # type: ignore[arg-type]

    # serverは変わらない
    assert received_scopes[0]["server"][0] == "localhost"
    # 警告が出る
    assert any("許可リスト外" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_forwarded_host_crlf_rejected(caplog):
    """CRLF混入X-Forwarded-Hostが反映されないことのテスト。"""
    _, middleware = _make_app({"x_host": 1})

    received_scopes: list[dict] = []

    async def fake_asgi(scope: typing.Any, receive: typing.Any, send: typing.Any) -> None:
        del receive, send
        received_scopes.append(scope)

    middleware.asgi_app = fake_asgi

    with caplog.at_level(logging.WARNING, logger="pytilpack.quart.proxy_fix"):
        scope = _make_scope([(b"x-forwarded-host", b"evil.com\r\nX-Injected: bad")])
        await middleware(scope, _noop_receive, _noop_send)  # type: ignore[arg-type]

    assert received_scopes[0]["server"][0] == "localhost"
    assert any("不正な値" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_static_prefix_scope_root_path_is_set():
    """static_prefix指定時にリクエストのroot_pathが設定されることのテスト。"""
    app, middleware = _make_app({"static_prefix": "/myapp", "x_prefix": 1})

    received_scopes: list[dict] = []

    async def fake_asgi(scope: typing.Any, receive: typing.Any, send: typing.Any) -> None:
        del receive, send
        received_scopes.append(scope)

    middleware.asgi_app = fake_asgi

    scope = _make_scope([(b"x-forwarded-prefix", b"/myapp")])
    await middleware(scope, _noop_receive, _noop_send)  # type: ignore[arg-type]

    assert received_scopes[0]["root_path"] == "/myapp"
    # app.configは初期化時から変わらない
    assert app.config["APPLICATION_ROOT"] == "/myapp"
