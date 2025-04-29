"""FastAPI関連のユーティリティ。"""

import io
import logging
import pathlib
import typing

import httpx

import pytilpack.pytest_
import pytilpack.web

logger = logging.getLogger(__name__)


def assert_bytes(
    response: httpx.Response,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = None,
) -> bytes:
    """fastapiのテストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスボディ

    """
    response_body = response.content

    try:
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        pytilpack.web.check_content_type(response.content_type, content_type)
    except AssertionError as e:
        logger.info(f"{e}\n\n{response_body!r}")
        raise e

    return response_body


def assert_html(
    response: httpx.Response,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "__default__",
    tmp_path: pathlib.Path | None = None,
    strict: bool = False,
) -> str:
    """fastapiのテストコード用。

    html5libが必要なので注意。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type
        tmp_path: 一時ファイルを保存するディレクトリ
        strict: HTML解析を厳格に行うかどうか

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスボディ (bs4.BeautifulSoup)

    """
    import html5lib

    response_body = response.text

    try:
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        if content_type == "__default__":
            content_type = ["text/html", "application/xhtml+xml"]
        pytilpack.web.check_content_type(response.content_type, content_type)

        # HTMLのチェック
        parser = html5lib.HTMLParser(strict=strict, debug=True)
        try:
            _ = parser.parse(io.BytesIO(response.content))
        except html5lib.html5parser.ParseError as e:
            raise AssertionError(f"HTMLエラー: {e}") from e
    except AssertionError as e:
        tmp_file_path = pytilpack.pytest_.create_temp_view(
            tmp_path, response_body, ".html"
        )
        raise AssertionError(f"{e} (HTML: {tmp_file_path} )") from e

    return response_body


def assert_json(
    response: httpx.Response,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "application/json",
) -> dict[str, typing.Any]:
    """fastapiのテストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスのjson

    """
    response_body = response.text

    try:
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        pytilpack.web.check_content_type(response.content_type, content_type)

        # JSONのチェック
        try:
            data = response.json()
        except Exception as e:
            raise AssertionError(f"JSONエラー: {e}") from e
    except AssertionError as e:
        logger.info(f"{e}\n\n{response_body!r}")
        raise e

    return data
