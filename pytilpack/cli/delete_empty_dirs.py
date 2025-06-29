"""空のディレクトリを削除するCLIユーティリティ。"""

import argparse
import pathlib

import pytilpack.pathlib


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """delete-empty-dirsサブコマンドのパーサーを追加します。"""
    parser = subparsers.add_parser(
        "delete-empty-dirs",
        help="空のディレクトリを削除",
        description="空のディレクトリを削除します",
    )
    parser.add_argument(
        "path",
        type=str,
        help="対象のディレクトリパス",
    )
    parser.add_argument(
        "--no-keep-root",
        action="store_false",
        dest="keep_root",
        help="空の場合はルートディレクトリも削除（デフォルトは保持）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="詳細なログを出力",
    )


def run(args: argparse.Namespace) -> None:
    """delete-empty-dirsコマンドを実行します。"""
    pytilpack.pathlib.delete_empty_dirs(
        pathlib.Path(args.path),
        keep_root=args.keep_root,
    )
