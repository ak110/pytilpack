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
    # import できないサブコマンドは「スタブ」として登録し、
    # 実行時に明確なエラーメッセージへ誘導する。
    loaded: dict[str, types.ModuleType] = {}
    unavailable: dict[str, tuple[str | None, ImportError]] = {}

    parser = argparse.ArgumentParser(
        prog="pytilpack",
        description="pytilpackコマンドラインツール",
    )
    subparsers = parser.add_subparsers(dest="command", help="コマンド")
    for name, module_path, extras in _SUBCOMMANDS:
        _register(subparsers, name, module_path, extras, loaded, unavailable)

    # argparse に渡す前に先頭の非オプション引数を確認する。
    # 利用不能なサブコマンドが指定された場合、argparse の --help や
    # unrecognized arguments 処理よりも前に統一エラーへ誘導する。
    for token in argv:
        if token.startswith("-"):
            continue
        if token in unavailable:
            _die_unavailable(token, *unavailable[token])
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
    if args.command in unavailable:
        # 先読みで捕捉できなかった場合の保険ルート。
        _die_unavailable(args.command, *unavailable[args.command])
    loaded[args.command].run(args)


def _register(
    subparsers: argparse._SubParsersAction,
    name: str,
    module_path: str,
    extras: str | None,
    loaded: dict[str, types.ModuleType],
    unavailable: dict[str, tuple[str | None, ImportError]],
) -> None:
    """サブコマンドを登録する。

    モジュールの import に失敗した場合でも、外部パッケージ由来の失敗であれば
    スタブサブパーサとして登録し、本物のバグは再送出する。
    判別可能な外部パッケージ起因の import 失敗が CLI 全体の起動を妨げないようにする。
    """
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        if not _is_external_import_failure(e, module_path):
            raise
        unavailable[name] = (extras, e)
        stub = subparsers.add_parser(
            name,
            add_help=False,
            help=(
                f"(未インストール: extras [{extras}] が必要)"
                if _is_missing_optional_dep(extras, e)
                else "(利用不可: 依存パッケージの読み込みに失敗)"
            ),
        )
        # argparse にパースエラーを発生させないため、残りの引数を全て吸収する。
        # 実際の dispatch は main() 冒頭の先読みルートが担うが、万一そちらを
        # すり抜けたケースでも `args.command == name` で unavailable ルートへ遷移する。
        stub.add_argument("_rest", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
        return
    module.add_parser(subparsers)
    loaded[name] = module


def _is_external_import_failure(exc: ImportError, module_path: str) -> bool:
    """`ImportError` が pytilpack 外のパッケージに由来するものか判定する。

    `pytilpack.cli.xxx` 自体が見つからない等の本物のバグは False を返し、
    呼び出し元で再送出させる。判別材料となる `name` を持たない場合も
    握り潰しを避けるため False を返す。
    """
    name = exc.name
    if name is None:
        return False
    # 自パッケージ配下のモジュールが見つからないケースはバグ扱い。
    root = module_path.split(".", 1)[0]
    return name != root and not name.startswith(f"{root}.")


def _is_missing_optional_dep(extras: str | None, exc: ImportError) -> bool:
    """extras対象の依存パッケージが見つからない失敗か判定する。"""
    return extras is not None and isinstance(exc, ModuleNotFoundError)


def _die_unavailable(command: str, extras: str | None, exc: ImportError) -> None:
    """サブコマンドが利用できない理由を表示して終了する。"""
    if _is_missing_optional_dep(extras, exc):
        print(
            f"pytilpack {command}: extras [{extras}] が必要です。\n"
            f"  pip install 'pytilpack[{extras}]'\n"
            f"  uvx --from 'pytilpack[{extras}]' pytilpack {command}",
            file=sys.stderr,
        )
    else:
        install_target = f"'pytilpack[{extras}]'" if extras is not None else "pytilpack"
        print(
            f"pytilpack {command}: 依存パッケージ {exc.name!r} の読み込みに失敗しました ({type(exc).__name__})。\n"
            "  依存パッケージの版が pytilpack へ対応していない可能性があります。\n"
            f"  pip install -U {install_target} で更新してください。",
            file=sys.stderr,
        )
    sys.exit(2)


if __name__ == "__main__":
    main()
