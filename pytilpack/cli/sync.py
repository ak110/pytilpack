"""ディレクトリ同期コマンド。"""

import argparse
import pathlib

import pytilpack.pathlib


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """syncサブコマンドのパーサーを追加します。"""
    parser = subparsers.add_parser(
        "sync",
        help="ディレクトリを同期",
        description="ディレクトリを同期します",
    )
    parser.add_argument(
        "src",
        help="コピー元のパス",
        type=str,
    )
    parser.add_argument(
        "dst",
        help="コピー先のパス",
        type=str,
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="コピー元に存在しないコピー先のファイル・ディレクトリを削除",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="詳細なログを出力",
    )


def run(args: argparse.Namespace) -> None:
    """syncコマンドを実行します。"""
    pytilpack.pathlib.sync(
        pathlib.Path(args.src),
        pathlib.Path(args.dst),
        delete=args.delete,
    )
