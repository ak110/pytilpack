#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<4.0"
# dependencies = ["pytilpack"]
# ///
"""空のディレクトリを削除するCLIユーティリティ。"""

import argparse
import logging
import pathlib

import pytilpack.pathlib


def main() -> None:
    """空のディレクトリを削除します。"""
    parser = argparse.ArgumentParser(description="空のディレクトリを削除します")
    parser.add_argument("path", type=pathlib.Path, help="対象のディレクトリパス")
    parser.add_argument(
        "--no-keep-root",
        action="store_false",
        dest="keep_root",
        help="空の場合はルートディレクトリも削除（デフォルトは保持）",
    )
    parser.add_argument("--verbose", action="store_true", help="詳細なログを出力")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)-5s] %(message)s",
    )

    pytilpack.pathlib.delete_empty_dirs(args.path, keep_root=args.keep_root)


if __name__ == "__main__":
    main()
