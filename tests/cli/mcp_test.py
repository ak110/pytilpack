"""mcp.pyのテスト。"""

import argparse
import typing

import mcp.server.mcpserver
import pytest

import pytilpack.cli.mcp


@pytest.mark.parametrize(
    ("transport", "expected_kwargs"),
    [
        ("stdio", {"transport": "stdio"}),
        (
            "http",
            {
                "transport": "streamable-http",
                "host": "example.com",
                "port": 9000,
            },
        ),
    ],
)
def test_run_passes_transport_arguments(
    monkeypatch: pytest.MonkeyPatch,
    transport: str,
    expected_kwargs: dict[str, object],
) -> None:
    """通信方式ごとの引数をMCP SDKへ渡す。"""
    calls: list[dict[str, object]] = []

    def fake_run(
        _server: mcp.server.mcpserver.MCPServer,
        **kwargs: typing.Any,
    ) -> None:
        calls.append(dict(kwargs))

    monkeypatch.setattr(mcp.server.mcpserver.MCPServer, "run", fake_run)
    args = argparse.Namespace(
        transport=transport,
        host="example.com",
        port=9000,
    )

    pytilpack.cli.mcp.run(args)

    assert calls == [expected_kwargs]
