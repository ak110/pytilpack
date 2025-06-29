"""古いファイルを削除するCLIユーティリティ。"""

import argparse
import datetime
import pathlib

import pytilpack.pathlib


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """delete-old-filesサブコマンドのパーサーを追加します。"""
    parser = subparsers.add_parser(
        "delete-old-files",
        help="古いファイルを削除",
        description="古いファイルを削除します",
    )
    parser.add_argument(
        "path",
        type=str,
        help="対象のディレクトリパス",
    )
    parser.add_argument(
        "--days",
        type=float,
        required=True,
        help="指定した日数より古いファイルを削除",
    )
    parser.add_argument(
        "--no-delete-empty-dirs",
        action="store_false",
        dest="delete_empty_dirs",
        help="空のディレクトリを削除しない（デフォルトは削除）",
    )
    parser.add_argument(
        "--no-keep-root-empty-dir",
        action="store_false",
        dest="keep_root_empty_dir",
        help="空の場合はルートディレクトリも削除（デフォルトは保持）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="詳細なログを出力",
    )


def run(args: argparse.Namespace) -> None:
    """delete-old-filesコマンドを実行します。"""
    days = max(0, args.days)
    before = datetime.datetime.now() - datetime.timedelta(days=days)
    pytilpack.pathlib.delete_old_files(
        pathlib.Path(args.path),
        before=before,
        delete_empty_dirs=args.delete_empty_dirs,
        keep_root_empty_dir=args.keep_root_empty_dir,
    )
