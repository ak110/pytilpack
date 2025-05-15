"""FastAPIのテストコード用アサーション関数。"""

import io
import json
import logging
import pathlib
import typing
import xml.etree.ElementTree

import httpx

import pytilpack.pytest_
import pytilpack.web

logger = logging.getLogger(__name__)


def assert_bytes(
    response: httpx.Response,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = None,
) -> bytes:
    """テストコード用。

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
        content_type_value = response.headers.get("content-type")
        pytilpack.web.check_content_type(content_type_value, content_type)
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
    """テストコード用。

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
    response_body = response.text

    try:
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        if content_type == "__default__":
            content_type = ["text/html", "application/xhtml+xml"]
        content_type_value = response.headers.get("content-type")
        pytilpack.web.check_content_type(content_type_value, content_type)

        # HTMLのチェック
        pytilpack.web.check_html(io.BytesIO(response.content), strict=strict)
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
    """テストコード用。

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
        content_type_value = response.headers.get("content-type")
        pytilpack.web.check_content_type(content_type_value, content_type)

        # JSONのチェック
        try:
            data = json.loads(response_body)
        except Exception as e:
            raise AssertionError(f"JSONエラー: {e}") from e
    except AssertionError as e:
        logger.info(f"{e}\n\n{response_body!r}")
        raise e

    return data


def assert_xml(
    response: httpx.Response,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "__default__",
) -> str:
    """テストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスのxml

    """
    response_body = response.text

    try:
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        if content_type == "__default__":
            content_type = ["text/xml", "application/xml"]
        content_type_value = response.headers.get("content-type")
        pytilpack.web.check_content_type(content_type_value, content_type)

        # XMLのチェック
        try:
            _ = xml.etree.ElementTree.fromstring(response_body)
        except Exception as e:
            raise AssertionError(f"XMLエラー: {e}") from e
    except AssertionError as e:
        logger.info(f"{e}\n\n{response_body!r}")
        raise e

    return response_body
