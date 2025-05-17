"""古いファイルを削除するCLIユーティリティ。"""

import argparse
import datetime
import logging
import pathlib

import pytilpack.pathlib_


def main() -> None:
    """古いファイルを削除します。"""
    parser = argparse.ArgumentParser(description="古いファイルを削除します")
    parser.add_argument("path", type=pathlib.Path, help="対象のディレクトリパス")
    parser.add_argument(
        "--days", type=float, required=True, help="指定した日数より古いファイルを削除"
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
    parser.add_argument("--verbose", action="store_true", help="詳細なログを出力")
    args = parser.parse_args()

    # ログの設定
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )

    days = max(0, args.days)  # 負の値は0として扱う
    before = datetime.datetime.now() - datetime.timedelta(days=days)
    pytilpack.pathlib_.delete_old_files(
        args.path,
        before=before,
        delete_empty_dirs=args.delete_empty_dirs,
        keep_root_empty_dir=args.keep_root_empty_dir,
    )


if __name__ == "__main__":
    main()
