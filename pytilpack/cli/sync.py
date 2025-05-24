"""ディレクトリ同期コマンド。"""

import argparse
import logging
import pathlib

import pytilpack.pathlib_

logger = logging.getLogger(__name__)


def main() -> None:
    """コマンドラインエントリポイント。"""
    parser = argparse.ArgumentParser(description="ディレクトリを同期します。")
    parser.add_argument("src", help="コピー元のパス", type=pathlib.Path)
    parser.add_argument("dst", help="コピー先のパス", type=pathlib.Path)
    parser.add_argument(
        "--delete",
        action="store_true",
        help="コピー元に存在しないコピー先のファイル・ディレクトリを削除",
    )
    parser.add_argument("--verbose", action="store_true", help="詳細なログを出力")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )

    pytilpack.pathlib_.sync(args.src, args.dst, delete=args.delete)


if __name__ == "__main__":
    main()
