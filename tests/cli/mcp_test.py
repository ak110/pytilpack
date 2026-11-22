import asyncio
import contextlib
import http.server
import pathlib
import re
import sys
import threading
from collections.abc import Iterator

import mcp
import mcp.client.stdio
import mcp.client.streamable_http
import pytest


@pytest.fixture(name="page_url")
def _page_url() -> Iterator[str]:

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            body = b"MCP fixture page"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/"
        finally:
            server.shutdown()
            thread.join()


def _assert_fetch_result(result: mcp.types.CallToolResult) -> None:
    assert not result.is_error
    assert any(item.type == "text" and "MCP fixture page" in item.text for item in result.content)


@pytest.mark.asyncio
async def test_mcp_stdio_fetch_url(page_url: str) -> None:
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
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "pytilpack.cli.main",
        "mcp",
        "--transport",
        "http",
        "--host",
        "127.0.0.1",
        "--port",
        "0",
        cwd=pathlib.Path(__file__).parents[2],
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    assert process.stderr is not None
    startup: list[str] = []
    try:
        try:
            async with asyncio.timeout(30):
                while line_bytes := await process.stderr.readline():
                    line = line_bytes.decode("utf-8", errors="replace")
                    startup.append(line)
                    if match := re.search(r"Uvicorn running on http://127\.0\.0\.1:([1-9][0-9]*)", line):
                        port = int(match[1])
                        break
                else:
                    raise AssertionError(f"MCPサーバーが終了した: {''.join(startup)}")
        except TimeoutError as exc:
            raise AssertionError(f"MCPサーバーの起動完了を確認できない: {''.join(startup)}") from exc

        async with asyncio.timeout(30), contextlib.AsyncExitStack() as stack:
            read_stream, write_stream = await stack.enter_async_context(
                mcp.client.streamable_http.streamable_http_client(f"http://127.0.0.1:{port}/mcp")
            )
            session = await stack.enter_async_context(mcp.ClientSession(read_stream, write_stream))
            await session.initialize()
            result = await session.call_tool("fetch_url", {"url": page_url})
        _assert_fetch_result(result)
    finally:
        if process.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                process.terminate()
        try:
            await asyncio.wait_for(process.communicate(), timeout=5)
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                process.kill()
            await asyncio.wait_for(process.communicate(), timeout=5)
