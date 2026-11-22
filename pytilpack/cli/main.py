__lazy_modules__ = ["argparse", "importlib", "logging", "sys", "types"]

import argparse
import importlib
import logging
import sys
import types

logger = logging.getLogger(__name__)

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
    argv = sys.argv[1:] if sys_args is None else list(sys_args)

    loaded: dict[str, types.ModuleType] = {}
    unavailable: dict[str, tuple[str | None, ImportError]] = {}

    parser = argparse.ArgumentParser(
        prog="pytilpack",
        description="pytilpackコマンドラインツール",
    )
    subparsers = parser.add_subparsers(dest="command", help="コマンド")
    for name, module_path, extras in _SUBCOMMANDS:
        _register(subparsers, name, module_path, extras, loaded, unavailable)

    for token in argv:
        if token.startswith("-"):
            continue
        if token in unavailable:
            _die_unavailable(token, *unavailable[token])
        break

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        print(
            "pytilpack: サブコマンドが指定されていません。使い方に示したサブコマンドのいずれかを指定して再実行してください。\n"
            "  例: pytilpack delete-empty-dirs <ディレクトリ>\n"
            "  各サブコマンドの使い方: pytilpack <サブコマンド> --help",
            file=sys.stderr,
        )
        sys.exit(1)

    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="[%(levelname)-5s] %(message)s",
    )

    if args.command in unavailable:
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
    try:
        module = importlib.import_module(module_path)
    except ImportError as raised:
        e = _resolve_import_error(raised)
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
        stub.add_argument("_rest", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
        return
    module.add_parser(subparsers)
    loaded[name] = module


# SQLAlchemy 2.1のasyncioモジュールのように、
# ModuleNotFoundErrorをnameの無いImportErrorへ包み直して送出するパッケージがあるため、
# __cause__をたどってnameを持つImportErrorを探す。
def _resolve_import_error(exc: ImportError) -> ImportError:
    current: BaseException | None = exc
    while isinstance(current, ImportError):
        if current.name is not None:
            return current
        current = current.__cause__
    return exc


def _is_external_import_failure(exc: ImportError, module_path: str) -> bool:
    name = exc.name
    if name is None:
        return False
    root = module_path.split(".", 1)[0]
    return name != root and not name.startswith(f"{root}.")


def _is_missing_optional_dep(extras: str | None, exc: ImportError) -> bool:
    return extras is not None and isinstance(exc, ModuleNotFoundError)


def _die_unavailable(command: str, extras: str | None, exc: ImportError) -> None:
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
