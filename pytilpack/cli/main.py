"""pytilpackメインCLIエントリーポイント。"""

import argparse
import logging
import sys

import pytilpack.cli.delete_empty_dirs
import pytilpack.cli.delete_old_files
import pytilpack.cli.fetch
import pytilpack.cli.mcp
import pytilpack.cli.sync


def main(sys_args: list[str] | None = None) -> None:
    """メインのエントリーポイント。"""
    parser = argparse.ArgumentParser(
        prog="pytilpack",
        description="pytilpackコマンドラインツール",
    )
    subparsers = parser.add_subparsers(dest="command", help="コマンド")
    pytilpack.cli.delete_empty_dirs.add_parser(subparsers)
    pytilpack.cli.delete_old_files.add_parser(subparsers)
    pytilpack.cli.sync.add_parser(subparsers)
    pytilpack.cli.fetch.add_parser(subparsers)
    pytilpack.cli.mcp.add_parser(subparsers)
    args = parser.parse_args(sys_args)
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # ログの基本設定
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="[%(levelname)-5s] %(message)s",
    )

    # 各サブコマンドの実行
    if args.command == "delete-empty-dirs":
        pytilpack.cli.delete_empty_dirs.run(args)
    elif args.command == "delete-old-files":
        pytilpack.cli.delete_old_files.run(args)
    elif args.command == "sync":
        pytilpack.cli.sync.run(args)
    elif args.command == "fetch":
        pytilpack.cli.fetch.run(args)
    elif args.command == "mcp":
        pytilpack.cli.mcp.run(args)


if __name__ == "__main__":
    main()
