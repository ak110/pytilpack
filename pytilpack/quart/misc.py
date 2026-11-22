__lazy_modules__ = [
    "asyncio",
    "contextlib",
    "dataclasses",
    "functools",
    "httpx",
    "logging",
    "os",
    "pytilpack.web",
    "quart",
    "quart.utils",
    "socket",
    "threading",
    "time",
    "typing",
    "uvicorn",
]

import asyncio
import contextlib
import dataclasses
import functools
import logging
import os
import socket
import threading
import time
import typing

import httpx
import quart
import quart.utils
import uvicorn

import pytilpack.web

__all__ = [
    "ConcurrencyState",
    "set_max_concurrency",
    "exhaust_concurrency",
    "run_sync",
    "get_next_url",
    "prefer_markdown",
    "static_url_for",
    "RouteInfo",
    "get_routes",
    "run",
]

logger = logging.getLogger(__name__)

_TIMESTAMP_CACHE: dict[str, int] = {}


@dataclasses.dataclass
class ConcurrencyState:
    semaphore: asyncio.Semaphore
    max_concurrency: int
    timeout: float | None


def set_max_concurrency(app: quart.Quart, max_concurrency: int, timeout: float | None = 3.0) -> None:
    if max_concurrency < 1:
        raise ValueError("max_concurrency must be >= 1")
    if "pytilpack_concurrency" in app.extensions:
        raise RuntimeError(
            "set_max_concurrency is already configured on this app. Call set_max_concurrency() only once per app."
        )

    semaphore = asyncio.Semaphore(max_concurrency)
    state = ConcurrencyState(
        semaphore=semaphore,
        max_concurrency=max_concurrency,
        timeout=timeout,
    )
    app.extensions["pytilpack_concurrency"] = state

    async def _acquire() -> None:
        sem = state.semaphore
        to = state.timeout
        try:
            if to is None:
                await sem.acquire()
            else:
                await asyncio.wait_for(sem.acquire(), timeout=to)
        except TimeoutError:
            logger.warning(
                f"Concurrency limit reached, aborting request with 503: {quart.request.path}."
                " No action is needed for occasional bursts; if this persists, raise max_concurrency or timeout"
                " of set_max_concurrency()."
            )
            quart.abort(
                503,
                description="サーバーが混みあっています。しばらく待ってから再度お試しください。",
            )
        # asyncio.CancelledError はここでは捕捉しない。
        # - to is None 経路（await sem.acquire() 直接）: acquire 待機中にキャンセルされると
        #   セマフォ未取得のまま CancelledError が伝播するため、漏洩は発生しない。
        # - to is not None 経路（asyncio.wait_for 経由）: wait_for がキャンセルされた場合、
        #   CPython の保証により acquire 完了済みであれば内部で release 済み。
        #   未完了であれば未取得のまま伝播する。
        # いずれの経路でも、この時点では未取得状態が保証されるため保護は不要。

        try:
            quart.g.quart__concurrency_token = True
        except BaseException:
            sem.release()
            raise

    async def _release(_: typing.Any) -> None:
        if hasattr(quart.g, "quart__concurrency_token"):
            state.semaphore.release()
            del quart.g.quart__concurrency_token

    app.before_request(_acquire)
    app.teardown_request(_release)


@contextlib.asynccontextmanager
async def exhaust_concurrency(app: quart.Quart):
    state: ConcurrencyState = app.extensions["pytilpack_concurrency"]
    original_semaphore = state.semaphore
    original_timeout = state.timeout

    state.semaphore = asyncio.Semaphore(0)
    state.timeout = 0.01

    try:
        yield
    finally:
        state.semaphore = original_semaphore
        state.timeout = original_timeout


def run_sync[**P, R](
    func: typing.Callable[P, R],
) -> typing.Callable[P, typing.Awaitable[R]]:

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        result = await quart.utils.run_sync(func)(*args, **kwargs)
        return typing.cast(R, result)

    return wrapper


def get_next_url() -> str:
    return pytilpack.web.build_next_url(
        quart.request.script_root,
        quart.request.path,
        quart.request.query_string.decode("utf-8"),
    )


def prefer_markdown() -> bool:
    return pytilpack.web.is_prefer_markdown(quart.request.headers.get("Accept", ""))


def static_url_for(
    filename: str,
    cache_busting: bool = True,
    cache_timestamp: bool | typing.Literal["when_not_debug"] = "when_not_debug",
    **kwargs: typing.Any,
) -> str:
    return pytilpack.web.resolve_static_url(
        quart.current_app.static_folder,
        filename,
        bool(quart.current_app.debug),
        cache_busting,
        cache_timestamp,
        lambda **kw: quart.url_for("static", **kw),
        _TIMESTAMP_CACHE,
        **kwargs,
    )


RouteInfo = pytilpack.web.RouteInfo


def get_routes(app: quart.Quart) -> list[RouteInfo]:
    return pytilpack.web.build_routes(app.url_map.iter_rules(), app.config.get("APPLICATION_ROOT"))


# port=0でアドレスごとにOSへ割り当てを任せるとIPv4とIPv6で別のポートになり、localhostへの接続が待ち受けていない側へ向かう。
# Windowsでは拒否の応答まで約2秒かかりタイムアウトするため、最初のアドレスで決まったポートを残りのアドレスでも使う。
def _bind_listen_sockets(host: str, port: int) -> list[socket.socket]:
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, flags=socket.AI_PASSIVE)
    addresses = list(dict.fromkeys((family, sockaddr[0]) for family, _, _, _, sockaddr in infos))
    for _ in range(10):
        sockets: list[socket.socket] = []
        bound_port = port
        try:
            for family, address in addresses:
                sock = socket.socket(family, socket.SOCK_STREAM)
                sockets.append(sock)
                # WindowsのSO_REUSEADDRは使用中のポートへの重複bindを許すため、POSIXだけで指定する
                if os.name == "posix":
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if family == socket.AF_INET6:
                    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                sock.bind((address, bound_port))
                bound_port = sock.getsockname()[1]
        except OSError:
            for sock in sockets:
                sock.close()
            if port != 0 or len(sockets) <= 1:
                raise
            continue
        return sockets
    raise OSError(f"{host}の全アドレスで共通の空きポートを確保できなかった")


@contextlib.asynccontextmanager
async def run(app: quart.Quart, host: str = "localhost", port: int = 5000):
    if not any(rule.endpoint == "_pytilpack_quart_dummy" for rule in app.url_map.iter_rules()):

        @app.route("/_pytilpack_quart_dummy")
        async def _pytilpack_quart_dummy():
            return "OK"

    try:
        listen_sockets = _bind_listen_sockets(host, port)
    except OSError as e:
        raise RuntimeError(
            "Quartサーバーの起動に失敗しました。原因は連鎖した例外を参照し、host・portの指定（使用中のポートなど）を見直す"
        ) from e

    config = uvicorn.Config(app=app, host=host, port=port, timeout_graceful_shutdown=1)
    server = uvicorn.Server(config)

    failures: list[BaseException] = []

    def run_server():
        try:
            asyncio.run(server.serve(sockets=listen_sockets))
        except BaseException as exc:
            failures.append(exc)

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    try:
        async with httpx.AsyncClient() as client:
            deadline = time.monotonic() + 10.0
            while True:
                if not thread.is_alive():
                    raise RuntimeError(
                        "Quartサーバーの起動に失敗しました。原因は連鎖した例外を参照し、host・portの指定（使用中のポートなど）を見直す"
                    ) from (failures[0] if failures else None)
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        "Quartサーバーの起動待ちが10秒を超えました。host・portへ接続できるか（ファイアウォール、名前解決）を確かめて再実行する"
                    )
                servers = getattr(server, "servers", [])
                sockets = [sock for srv in servers for sock in (srv.sockets or [])]
                if not server.started or not sockets:
                    await asyncio.sleep(0.05)
                    continue
                actual_port = int(sockets[0].getsockname()[1])
                try:
                    response = await client.get(f"http://{host}:{actual_port}/_pytilpack_quart_dummy", timeout=0.2)
                    response.raise_for_status()
                    break
                except httpx.HTTPError:
                    await asyncio.sleep(0.1)

        yield actual_port

    finally:
        server.should_exit = True
        await asyncio.to_thread(thread.join, 5.0)
        if thread.is_alive():
            server.force_exit = True
            await asyncio.to_thread(thread.join, 2.0)
        if not thread.is_alive():
            for sock in listen_sockets:
                sock.close()
        if thread.is_alive():
            raise RuntimeError(
                "Quartサーバーの停止に失敗しました。強制終了の要求後もサーバースレッドが終了せずdaemonスレッドとして残っている。"
                "終了しないリクエスト処理が無いかを確かめる"
            )
