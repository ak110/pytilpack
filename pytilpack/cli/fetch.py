"""URLアクセスコマンド。"""

__lazy_modules__ = ["argparse", "httpx", "logging", "pathlib", "pytilpack.htmlrag", "sys"]

import argparse
import logging
import pathlib
import sys

import httpx

import pytilpack.htmlrag

logger = logging.getLogger(__name__)


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """fetchサブコマンドのパーサーを追加する。"""
    parser = subparsers.add_parser(
        "fetch",
        help="URLの内容を取得",
        description=(
            "URL先の本文を取得して標準出力に出力します。"
            "HTMLは簡略化し、他のテキスト形式・JSON・XMLはそのまま出力します。"
            "接続エラーと一時的なHTTPエラーは再試行し、HTTPエラーと扱えない形式は終了コード1で終了します"
        ),
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
        "--raw",
        action="store_true",
        help="HTMLを簡略化せず、取得した本文をそのまま出力する",
    )
    parser.add_argument(
        "-O",
        "--output-document",
        type=pathlib.Path,
        default=None,
        metavar="FILE",
        help="標準出力の代わりにFILEへ書き込む",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="通信ログなどの詳細なログを出力",
    )


def run(args: argparse.Namespace) -> None:
    """fetchコマンドを実行する。"""
    if not args.verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        output = pytilpack.htmlrag.fetch_url(
            url=args.url,
            no_verify=args.no_verify,
            accept=args.accept,
            user_agent=args.user_agent,
            raw=args.raw,
        )
    except RuntimeError as e:
        print(f"pytilpack fetch: {e}", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPError as e:
        print(f"pytilpack fetch: URL {args.url} の取得に失敗しました。{type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
    if args.output_document is None:
        print(output)
    else:
        args.output_document.write_text(output, encoding="utf-8", newline="")
