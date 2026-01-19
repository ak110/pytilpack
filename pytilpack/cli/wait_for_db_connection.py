"""DB接続待機コマンド。"""

import argparse
import asyncio
import logging

import pytilpack.sqlalchemy

logger = logging.getLogger(__name__)

# 非同期ドライバのリスト
ASYNC_DRIVERS = [
    "+asyncpg",
    "+aiosqlite",
    "+aiomysql",
    "+asyncmy",
    "+aiopg",
]


def is_async_url(url: str) -> bool:
    """URLが非同期ドライバを使用しているか判定する。"""
    return any(driver in url for driver in ASYNC_DRIVERS)


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """wait-for-db-connectionサブコマンドのパーサーを追加します。"""
    parser = subparsers.add_parser(
        "wait-for-db-connection",
        help="DB接続可能になるまで待機",
        description="指定されたSQLALCHEMY_DATABASE_URIでDBに接続可能になるまで待機します",
    )
    parser.add_argument(
        "url",
        help="SQLALCHEMY_DATABASE_URI",
        type=str,
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=180.0,
        help="タイムアウト秒数（デフォルト: 180）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="詳細なログを出力",
    )


def run(args: argparse.Namespace) -> None:
    """wait-for-db-connectionコマンドを実行します。"""
    if is_async_url(args.url):
        asyncio.run(pytilpack.sqlalchemy.await_for_connection(args.url, timeout=args.timeout))
    else:
        pytilpack.sqlalchemy.wait_for_connection(args.url, timeout=args.timeout)
