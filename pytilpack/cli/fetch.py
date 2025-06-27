#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<4.0"
# dependencies = ["pytilpack[htmlrag]", "httpx"]
# ///
"""URLアクセスコマンド。"""

import argparse
import logging

import httpx

import pytilpack.htmlrag

logger = logging.getLogger(__name__)


def main() -> None:
    """コマンドラインエントリポイント。"""
    parser = argparse.ArgumentParser(
        description="URL先のHTMLを取得し、簡略化して標準出力に出力します。"
    )
    parser.add_argument("url", help="URL", type=str)
    parser.add_argument(
        "--no-verify", action="store_true", help="SSL証明書の検証を無効化する。"
    )
    parser.add_argument("--verbose", action="store_true", help="詳細なログを出力")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)-5s] %(message)s",
    )

    r = httpx.get(args.url, verify=not args.no_verify, follow_redirects=True)
    if r.status_code != 200:
        logger.error(f"URL {args.url} の取得に失敗しました。\n{r.text}")
        return

    if "html" not in r.headers.get("Content-Type", "text/html"):
        logger.error(f"URL {args.url} はHTMLではありません。\n{r.text[:100]}...")
        return

    content = r.text
    output = pytilpack.htmlrag.clean_html(
        content, aggressive=True, keep_title=True, keep_href=True
    )
    print(output)


if __name__ == "__main__":
    main()
