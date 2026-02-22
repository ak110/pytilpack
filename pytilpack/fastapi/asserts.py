"""FastAPIのテストコード用アサーション関数。"""

import json
import pathlib
import typing
import xml.etree.ElementTree as ET

import httpx

import pytilpack.pytest
import pytilpack.web


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

    with pytilpack.pytest.AssertBlock(response_body, suffix=".txt"):  # binでは開けないのでとりあえずtxt
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        content_type_value = response.headers.get("content-type")
        pytilpack.web.check_content_type(content_type_value, content_type)

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

    if content_type == "__default__":
        content_type = ["text/html", "application/xhtml+xml"]

    with pytilpack.pytest.AssertBlock(response_body, suffix=".html", tmp_path=tmp_path):
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        content_type_value = response.headers.get("content-type")
        pytilpack.web.check_content_type(content_type_value, content_type)

        # HTMLのチェック
        pytilpack.web.check_html(response.content, strict=strict)

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
    data: dict[str, typing.Any]

    with pytilpack.pytest.AssertBlock(response_body, suffix=".json"):
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

    if content_type == "__default__":
        content_type = ["text/xml", "application/xml"]

    with pytilpack.pytest.AssertBlock(response_body, suffix=".xml"):
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        content_type_value = response.headers.get("content-type")
        pytilpack.web.check_content_type(content_type_value, content_type)

        # XMLのチェック
        try:
            _ = ET.fromstring(response_body)
        except Exception as e:
            raise AssertionError(f"XMLエラー: {e}") from e

    return response_body


def assert_sse(
    response: httpx.Response,
    status_code: int = 200,
) -> httpx.Response:
    """テストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード

    Raises:
        AssertionError: ステータスコードが異なる場合、またはContent-Typeが異なる場合

    Returns:
        レスポンス

    """
    pytilpack.web.check_status_code(response.status_code, status_code)
    content_type_value = response.headers.get("content-type")
    pytilpack.web.check_content_type(content_type_value, "text/event-stream")
    return response


def assert_response(
    response: httpx.Response,
    status_code: int = 200,
) -> httpx.Response:
    """テストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンス

    """
    pytilpack.web.check_status_code(response.status_code, status_code)
    return response
