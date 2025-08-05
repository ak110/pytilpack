"""MCPサーバーコマンド。"""

import argparse
import logging

from mcp.server.fastmcp import FastMCP

import pytilpack.htmlrag

logger = logging.getLogger(__name__)


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """mcpサブコマンドのパーサーを追加します。"""
    parser = subparsers.add_parser(
        "mcp",
        help="MCPサーバーを起動",
        description="Model Context ProtocolサーバーとしてpytilpackのFetch機能を提供します",
    )
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "http"],
        default="stdio",
        help="通信方式（デフォルト: stdio）",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="サーバーのホスト名（httpの場合のみ使用、デフォルト: localhost）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="サーバーのポート番号（httpの場合のみ使用、デフォルト: 8000）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="詳細なログを出力",
    )


def run(args: argparse.Namespace) -> None:
    """mcpコマンドを実行します。"""
    _run_server(transport=args.transport, host=args.host, port=args.port)


def _run_server(transport: str = "stdio", host: str = "localhost", port: int = 8000) -> None:
    """MCPサーバーを起動します。

    Args:
        transport: 通信方式（"stdio" または "http"）
        host: サーバーのホスト名（httpの場合のみ使用）
        port: サーバーのポート番号（httpの場合のみ使用）
    """
    if transport == "stdio":
        _create_server().run(transport="stdio")
    elif transport == "http":
        _create_server(host=host, port=port).run(transport="streamable-http")
    else:
        raise ValueError(f"サポートされていない通信方式です: {transport}")


def _create_server(**kwargs) -> FastMCP:
    """MCPサーバーインスタンスを作成します。"""
    mcp = FastMCP("pytilpack", instructions="pytilpackのユーティリティ機能を提供するMCPサーバー", **kwargs)

    @mcp.tool()
    def fetch_url(
        url: str,
        no_verify: bool = False,
        accept: str = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        user_agent: str | None = None,
    ) -> str:
        """URLからHTMLを取得し、簡略化して返します。

        Args:
            url: 取得するURL
            no_verify: SSL証明書の検証を無効化するかどうか
            accept: 受け入れるコンテンツタイプ
            user_agent: User-Agentヘッダー（未指定時はデフォルト値を使用）

        Returns:
            簡略化されたHTML内容
        """
        try:
            return pytilpack.htmlrag.fetch_url(
                url=url,
                no_verify=no_verify,
                accept=accept,
                user_agent=user_agent,
            )
        except Exception as e:
            logger.error(f"URL {url} の取得中にエラーが発生しました: {e}")
            return f"Error: URL {url} の取得中にエラーが発生しました: {e}"

    return mcp
