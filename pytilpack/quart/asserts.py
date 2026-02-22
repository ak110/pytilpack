"""Quartのテストコード用アサーション関数。"""

import json
import pathlib
import typing
import xml.etree.ElementTree as ET

import quart

import pytilpack.pytest
import pytilpack.web

ResponseType = quart.Response | typing.Awaitable[quart.Response]
"""レスポンスの型。"""


async def assert_bytes(
    response: ResponseType,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = None,
) -> bytes:
    """テストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type

    Raises:
        AssertionError: ステータスコードが異なる場合など

    Returns:
        レスポンスボディ

    """
    response = await _get_response(response)
    response_body = await response.get_data(as_text=False)

    async with pytilpack.pytest.AssertBlock(response_body, suffix=".txt"):  # binでは開けないのでとりあえずtxt
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        pytilpack.web.check_content_type(response.content_type, content_type)

    return response_body


async def assert_html(
    response: ResponseType,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "__default__",
    strict: bool = False,
    tmp_path: pathlib.Path | None = None,
) -> str:
    """テストコード用。

    html5libが必要なので注意。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type
        strict: Trueの場合、HTML5の仕様に従ったパースを行う
        tmp_path: 一時ファイルを保存するディレクトリ

    Raises:
        AssertionError: ステータスコードが異なる場合など

    Returns:
        レスポンスボディ (bs4.BeautifulSoup)

    """
    response = await _get_response(response)
    response_body = await response.get_data(as_text=True)
    response_bytes = await response.get_data(as_text=False)

    if content_type == "__default__":
        content_type = ["text/html", "application/xhtml+xml"]

    async with pytilpack.pytest.AssertBlock(response_body, suffix=".html", tmp_path=tmp_path):
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        pytilpack.web.check_content_type(response.content_type, content_type)

        # HTMLのチェック
        pytilpack.web.check_html(response_bytes, strict=strict)

    return response_body


async def assert_json(
    response: ResponseType,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "application/json",
) -> dict[str, typing.Any]:
    """テストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type

    Raises:
        AssertionError: ステータスコードが異なる場合など

    Returns:
        レスポンスのjson

    """
    response = await _get_response(response)
    response_body = await response.get_data(as_text=True)
    data: dict[str, typing.Any]

    async with pytilpack.pytest.AssertBlock(response_body, suffix=".json"):
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        pytilpack.web.check_content_type(response.content_type, content_type)

        # JSONのチェック
        try:
            data = json.loads(response_body)
        except Exception as e:
            raise AssertionError(f"JSONエラー: {e}") from e

    return data


async def assert_xml(
    response: ResponseType,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "__default__",
) -> str:
    """テストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type

    Raises:
        AssertionError: ステータスコードが異なる場合など

    Returns:
        レスポンスのxml

    """
    response = await _get_response(response)
    response_body = await response.get_data(as_text=True)

    if content_type == "__default__":
        content_type = ["text/xml", "application/xml"]

    async with pytilpack.pytest.AssertBlock(response_body, suffix=".xml"):
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        pytilpack.web.check_content_type(response.content_type, content_type)

        # XMLのチェック
        try:
            _ = ET.fromstring(response_body)
        except Exception as e:
            raise AssertionError(f"XMLエラー: {e}") from e

    return response_body


async def assert_sse(
    response: ResponseType,
    status_code: int = 200,
) -> quart.Response:
    """テストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード

    Raises:
        AssertionError: ステータスコードが異なる場合、またはContent-Typeが異なる場合

    Returns:
        レスポンス

    """
    response = await _get_response(response)
    pytilpack.web.check_status_code(response.status_code, status_code)
    pytilpack.web.check_content_type(response.content_type, "text/event-stream")
    return response


async def assert_response(
    response: ResponseType,
    status_code: int = 200,
) -> quart.Response:
    """テストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンス

    """
    response = await _get_response(response)
    pytilpack.web.check_status_code(response.status_code, status_code)
    return response


async def _get_response(response: ResponseType) -> quart.Response:
    if isinstance(response, typing.Awaitable):
        return await response
    return response
