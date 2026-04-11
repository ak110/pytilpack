"""pytilpackメインCLIエントリーポイント。"""

import argparse
import importlib
import logging
import sys
import types

logger = logging.getLogger(__name__)

# サブコマンドのレジストリ。
# (サブコマンド名, モジュールパス, extras 名)
# extras 名が None のものはベース依存のみで動作する。
_SUBCOMMANDS: list[tuple[str, str, str | None]] = [
    ("babel", "pytilpack.cli.babel", "babel"),
    ("delete-empty-dirs", "pytilpack.cli.delete_empty_dirs", None),
    ("delete-old-files", "pytilpack.cli.delete_old_files", None),
    ("sync", "pytilpack.cli.sync", None),
    ("fetch", "pytilpack.cli.fetch", None),
    ("mcp", "pytilpack.cli.mcp", None),
    ("wait-for-db-connection", "pytilpack.cli.wait_for_db_connection", "sqlalchemy"),
]


def main(sys_args: list[str] | None = None) -> None:
    """メインのエントリーポイント。"""
    argv = sys.argv[1:] if sys_args is None else list(sys_args)

    # サブコマンドを遅延登録する。
    # extras 欠落により import できないサブコマンドは「スタブ」として登録し、
    # 実行時に明確なエラーメッセージへ誘導する。
    loaded: dict[str, types.ModuleType] = {}
    missing: dict[str, str] = {}

    parser = argparse.ArgumentParser(
        prog="pytilpack",
        description="pytilpackコマンドラインツール",
    )
    subparsers = parser.add_subparsers(dest="command", help="コマンド")
    for name, module_path, extras in _SUBCOMMANDS:
        _register(subparsers, name, module_path, extras, loaded, missing)

    # argparse に渡す前に先頭の非オプション引数を確認する。
    # 未インストールサブコマンドが指定された場合、argparse の --help や
    # unrecognized arguments 処理よりも前に統一エラーへ誘導する。
    for token in argv:
        if token.startswith("-"):
            continue
        if token in missing:
            _die_missing_extras(token, missing[token])
        break

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # ログの基本設定
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="[%(levelname)-5s] %(message)s",
    )

    # 各サブコマンドの実行
    if args.command in missing:
        # 先読みで捕捉できなかった場合の保険ルート。
        _die_missing_extras(args.command, missing[args.command])
    loaded[args.command].run(args)


def _register(
    subparsers: argparse._SubParsersAction,
    name: str,
    module_path: str,
    extras: str | None,
    loaded: dict[str, types.ModuleType],
    missing: dict[str, str],
) -> None:
    """サブコマンドを登録する。

    モジュールの import に失敗した場合でも extras 由来の `ModuleNotFoundError`
    であればスタブサブパーサとして登録し、本物のバグは再送出する。
    """
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        if extras is None or not _is_optional_dep_missing(e, module_path):
            raise
        missing[name] = extras
        stub = subparsers.add_parser(
            name,
            add_help=False,
            help=f"(未インストール: extras [{extras}] が必要)",
        )
        # argparse にパースエラーを出させないため、残りの引数を全て吸収する。
        # 実際の dispatch は main() 冒頭の先読みルートが担うが、万一そちらを
        # すり抜けたケースでも `args.command == name` で missing ルートへ流れる。
        stub.add_argument("_rest", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
        return
    module.add_parser(subparsers)
    loaded[name] = module


def _is_optional_dep_missing(exc: ModuleNotFoundError, module_path: str) -> bool:
    """`ModuleNotFoundError` が extras 由来のパッケージ欠落によるものか判定する。

    `pytilpack.cli.xxx` 自体が見つからない等の本物のバグは False を返し、
    呼び出し元で再送出させる。
    """
    name = exc.name
    if name is None:
        return False
    # モジュール自身、またはその親パッケージが見つからないケースはバグ扱い。
    return name != module_path and not module_path.startswith(f"{name}.")


def _die_missing_extras(command: str, extras: str) -> None:
    """Extras 不足時のエラーメッセージを表示して終了する。"""
    print(
        f"pytilpack {command}: extras [{extras}] が必要です。\n"
        f"  pip install 'pytilpack[{extras}]'\n"
        f"  uvx --from 'pytilpack[{extras}]' pytilpack {command}",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
