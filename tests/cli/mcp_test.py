"""MCPサーバーを公開CLIから起動する結合テスト。"""

import asyncio
import contextlib
import http.server
import pathlib
import socket
import subprocess
import sys
import threading
from collections.abc import Iterator

import mcp
import mcp.client.stdio
import mcp.client.streamable_http
import pytest


@pytest.fixture(name="page_url")
def _page_url() -> Iterator[str]:
    """fetch_urlの入力に使うローカルHTTPページを提供する。"""

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            body = b"MCP fixture page"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def _assert_fetch_result(result: mcp.types.CallToolResult) -> None:
    """公開ツールがHTTPページ本文を返したことを確認する。"""
    assert not result.is_error
    assert any(item.type == "text" and "MCP fixture page" in item.text for item in result.content)


@pytest.mark.asyncio
async def test_mcp_stdio_fetch_url(page_url: str) -> None:
    """stdioのCLI起動からfetch_urlを呼ぶ。"""
    params = mcp.client.stdio.StdioServerParameters(
        command=sys.executable,
        args=["-m", "pytilpack.cli.main", "mcp", "--transport", "stdio"],
        cwd=pathlib.Path(__file__).parents[2],
    )
    async with contextlib.AsyncExitStack() as stack:
        read_stream, write_stream = await stack.enter_async_context(mcp.client.stdio.stdio_client(params))
        session = await stack.enter_async_context(mcp.ClientSession(read_stream, write_stream))
        await session.initialize()
        result = await session.call_tool("fetch_url", {"url": page_url})
    _assert_fetch_result(result)


@pytest.mark.asyncio
async def test_mcp_http_fetch_url(page_url: str) -> None:
    """HTTPのCLI起動からfetch_urlを呼ぶ。"""
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, "-m", "pytilpack.cli.main", "mcp", "--transport", "http", "--host", "127.0.0.1", "--port", str(port)],
        cwd=pathlib.Path(__file__).parents[2],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        for _ in range(50):
            if process.poll() is not None:
                raise AssertionError(f"MCPサーバーが終了した: {process.stderr.read() if process.stderr else ''}")
            try:
                _reader, writer = await asyncio.open_connection("127.0.0.1", port)
            except OSError:
                await asyncio.sleep(0.1)
            else:
                writer.close()
                await writer.wait_closed()
                break
        else:
            raise AssertionError("MCPサーバーが起動しなかった")

        async with contextlib.AsyncExitStack() as stack:
            read_stream, write_stream = await stack.enter_async_context(
                mcp.client.streamable_http.streamable_http_client(f"http://127.0.0.1:{port}/mcp")
            )
            session = await stack.enter_async_context(mcp.ClientSession(read_stream, write_stream))
            await session.initialize()
            result = await session.call_tool("fetch_url", {"url": page_url})
        _assert_fetch_result(result)
    finally:
        process.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.communicate(timeout=5)
        if process.poll() is None:
            process.kill()
            process.communicate()
