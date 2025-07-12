"""URLアクセスコマンド。"""

import argparse
import importlib.metadata
import logging

import httpx

import pytilpack.htmlrag

logger = logging.getLogger(__name__)


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """fetchサブコマンドのパーサーを追加します。"""
    version = importlib.metadata.version("pytilpack")

    parser = subparsers.add_parser(
        "fetch",
        help="URLの内容を取得",
        description="URL先のHTMLを取得し、簡略化して標準出力に出力します",
    )
    parser.add_argument(
        "url",
        help="URL",
        type=str,
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="SSL証明書の検証を無効化する",
    )
    parser.add_argument(
        "--accept",
        type=str,
        default="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        help="受け入れるコンテンツタイプ（デフォルト: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8）",
    )
    parser.add_argument(
        "--user-agent",
        type=str,
        default=f"pytilpack/{version} (+https://github.com/ak110/pytilpack)",
        help=f'User-Agentヘッダー（デフォルト: "pytilpack/{version} (+https://github.com/ak110/pytilpack)"）',
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="詳細なログを出力",
    )


def run(args: argparse.Namespace) -> None:
    """fetchコマンドを実行します。"""
    output = fetch_url(
        url=args.url,
        no_verify=args.no_verify,
        accept=args.accept,
        user_agent=args.user_agent,
    )
    print(output)


def fetch_url(
    url: str,
    no_verify: bool = False,
    accept: str = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    user_agent: str | None = None,
) -> str:
    """URLからHTMLを取得し、簡略化して返します。

    Args:
        url: 取得するURL
        no_verify: SSL証明書の検証を無効化するかどうか
        accept: 受け入れるコンテンツタイプ
        user_agent: User-Agentヘッダー（未指定時はデフォルト値を使用）

    Returns:
        簡略化されたHTML内容

    Raises:
        Exception: HTTP取得やHTMLパースでエラーが発生した場合
    """
    if user_agent is None:
        version = importlib.metadata.version("pytilpack")
        user_agent = f"pytilpack/{version} (+https://github.com/ak110/pytilpack)"

    r = httpx.get(
        url,
        headers={
            "Accept": accept,
            "User-Agent": user_agent,
        },
        verify=not no_verify,
        follow_redirects=True,
    )

    if r.status_code != 200:
        raise RuntimeError(f"URL {url} の取得に失敗しました。Status: {r.status_code}\n{r.text}")

    content_type = r.headers.get("Content-Type", "text/html")
    if "html" not in content_type:
        raise RuntimeError(f"URL {url} はHTMLではありません。Content-Type: {content_type}\n{r.text[:100]}...")

    content = r.text
    output = pytilpack.htmlrag.clean_html(
        content,
        aggressive=True,
        keep_title=True,
        keep_href=True,
    )
    return output
