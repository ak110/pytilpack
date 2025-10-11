"""URLアクセスコマンド。"""

import argparse
import logging

import pytilpack.htmlrag

logger = logging.getLogger(__name__)


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """fetchサブコマンドのパーサーを追加します。"""
    parser = subparsers.add_parser(
        "fetch",
        help="URLの内容を取得",
        description="URL先のHTMLを取得し、簡略化して標準出力に出力します",
    )
    parser.add_argument(
        "url",
        help="URL",
        type=str,
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="SSL証明書の検証を無効化する",
    )
    parser.add_argument(
        "--accept",
        type=str,
        default=pytilpack.htmlrag.DEFAULT_ACCEPT,
        help=f"受け入れるコンテンツタイプ（デフォルト: {pytilpack.htmlrag.DEFAULT_ACCEPT!r}）",
    )
    default_user_agent = pytilpack.htmlrag.get_default_user_agent()
    parser.add_argument(
        "--user-agent",
        type=str,
        default=default_user_agent,
        help=f"User-Agentヘッダー（デフォルト: {default_user_agent!r}）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="詳細なログを出力",
    )


def run(args: argparse.Namespace) -> None:
    """fetchコマンドを実行します。"""
    output = pytilpack.htmlrag.fetch_url(
        url=args.url,
        no_verify=args.no_verify,
        accept=args.accept,
        user_agent=args.user_agent,
    )
    print(output)
