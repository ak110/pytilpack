"""Babelメッセージ管理CLIユーティリティ。"""

import argparse
import logging
import pathlib

import babel.messages.catalog
import babel.messages.extract
import babel.messages.mofile
import babel.messages.pofile

logger = logging.getLogger(__name__)


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """babelサブコマンドのパーサーを追加する。"""
    parser = subparsers.add_parser(
        "babel",
        help="Babelメッセージ管理",
        description="gettextメッセージの抽出・初期化・更新・コンパイルを行う",
    )
    babel_sub = parser.add_subparsers(dest="babel_command", help="Babelサブコマンド")

    # extract サブコマンド
    extract_parser = babel_sub.add_parser("extract", help="メッセージを抽出する")
    extract_parser.add_argument("input_dirs", nargs="+", help="抽出元ディレクトリ")
    extract_parser.add_argument("-o", "--output", default="messages.pot", help="出力POTファイル")
    extract_parser.add_argument(
        "-k",
        "--keywords",
        nargs="*",
        default=None,
        help="キーワード（デフォルト: python標準）",
    )
    extract_parser.add_argument("--charset", default="utf-8", help="文字コード")

    # init サブコマンド
    init_parser = babel_sub.add_parser("init", help="新しいロケールのカタログを初期化する")
    init_parser.add_argument("-l", "--locale", required=True, help="ロケール")
    init_parser.add_argument("-i", "--input-file", default="messages.pot", help="入力POTファイル")
    init_parser.add_argument("-d", "--output-dir", default="locales", help="出力ディレクトリ")
    init_parser.add_argument("--domain", default="messages", help="ドメイン")

    # update サブコマンド
    update_parser = babel_sub.add_parser("update", help="既存カタログを更新する")
    update_parser.add_argument("-i", "--input-file", default="messages.pot", help="入力POTファイル")
    update_parser.add_argument("-d", "--output-dir", default="locales", help="出力ディレクトリ")
    update_parser.add_argument("--domain", default="messages", help="ドメイン")

    # compile サブコマンド
    compile_parser = babel_sub.add_parser("compile", help="カタログをコンパイルする")
    compile_parser.add_argument("-d", "--directory", default="locales", help="ロケールディレクトリ")
    compile_parser.add_argument("--domain", default="messages", help="ドメイン")


def run(args: argparse.Namespace) -> None:
    """babelコマンドを実行する。"""
    if args.babel_command == "extract":
        _run_extract(args)
    elif args.babel_command == "init":
        _run_init(args)
    elif args.babel_command == "update":
        _run_update(args)
    elif args.babel_command == "compile":
        _run_compile(args)
    else:
        logger.error("サブコマンドを指定してください: extract, init, update, compile")


def _run_extract(args: argparse.Namespace) -> None:
    """メッセージ抽出を実行する。"""
    output_path = pathlib.Path(args.output)
    catalog = babel.messages.catalog.Catalog(charset=args.charset)
    # 各ディレクトリからメッセージを抽出
    for input_dir in args.input_dirs:
        input_path = pathlib.Path(input_dir)
        if not input_path.is_dir():
            logger.warning(f"ディレクトリが存在しません: {input_path}")
            continue
        keywords = _parse_keywords(args.keywords) if args.keywords else babel.messages.extract.DEFAULT_KEYWORDS
        extracted = babel.messages.extract.extract_from_dir(
            str(input_path),
            keywords=keywords,
        )
        for filename, lineno, message, comments, context in extracted:
            catalog.add(
                message,
                locations=[(f"{input_dir}/{filename}", lineno)],
                auto_comments=comments,
                context=context,
            )
    # POTファイルに書き出し
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        babel.messages.pofile.write_po(f, catalog)
    logger.info(f"抽出完了: {output_path}")


def _run_init(args: argparse.Namespace) -> None:
    """新しいロケールのカタログを初期化する。"""
    input_path = pathlib.Path(args.input_file)
    output_dir = pathlib.Path(args.output_dir)
    locale = args.locale
    domain = args.domain
    # POTファイルを読み込み
    with input_path.open("rb") as f:
        catalog = babel.messages.pofile.read_po(f)
    catalog.locale = locale
    # 出力先ディレクトリを作成
    po_dir = output_dir / locale / "LC_MESSAGES"
    po_dir.mkdir(parents=True, exist_ok=True)
    po_path = po_dir / f"{domain}.po"
    with po_path.open("wb") as f:
        babel.messages.pofile.write_po(f, catalog)
    logger.info(f"初期化完了: {po_path}")


def _run_update(args: argparse.Namespace) -> None:
    """既存カタログを更新する。"""
    input_path = pathlib.Path(args.input_file)
    output_dir = pathlib.Path(args.output_dir)
    domain = args.domain
    # POTファイル（テンプレート）を読み込み
    with input_path.open("rb") as f:
        template = babel.messages.pofile.read_po(f)
    # 各ロケールのPOファイルを更新
    for locale_dir in sorted(output_dir.iterdir()):
        po_path = locale_dir / "LC_MESSAGES" / f"{domain}.po"
        if not po_path.exists():
            continue
        with po_path.open("rb") as f:
            catalog = babel.messages.pofile.read_po(f)
        catalog.update(template)
        with po_path.open("wb") as f:
            babel.messages.pofile.write_po(f, catalog)
        logger.info(f"更新完了: {po_path}")


def _run_compile(args: argparse.Namespace) -> None:
    """カタログをコンパイルする。"""
    directory = pathlib.Path(args.directory)
    domain = args.domain
    for locale_dir in sorted(directory.iterdir()):
        po_path = locale_dir / "LC_MESSAGES" / f"{domain}.po"
        if not po_path.exists():
            continue
        mo_path = po_path.with_suffix(".mo")
        with po_path.open("rb") as f:
            catalog = babel.messages.pofile.read_po(f)
        with mo_path.open("wb") as f:
            babel.messages.mofile.write_mo(f, catalog)
        logger.info(f"コンパイル完了: {mo_path}")


def _parse_keywords(keywords: list[str]) -> dict[str, tuple[int, ...] | None]:
    """キーワード文字列リストを辞書に変換する。"""
    result: dict[str, tuple[int, ...] | None] = {}
    for kw in keywords:
        if ":" in kw:
            name, nums = kw.split(":", 1)
            result[name] = tuple(int(n) for n in nums.split(","))
        else:
            result[kw] = None
    return result
