"""FastAPIのテストコード用アサーション関数。"""

import pathlib
import typing

import httpx

import pytilpack._web_asserts as _core

__all__ = [
    "assert_bytes",
    "assert_html",
    "assert_json",
    "assert_xml",
    "assert_sse",
    "assert_response",
]


def _content_type(response: httpx.Response) -> str | None:
    """httpxレスポンスのContent-Typeヘッダー値を返す。"""
    return response.headers.get("content-type")


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
    _core.assert_bytes_core(response_body, response.status_code, _content_type(response), status_code, content_type)
    return response_body


def assert_html(
    response: httpx.Response,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "__default__",
    strict: bool = False,
    tmp_path: pathlib.Path | None = None,
) -> str:
    """テストコード用。

    html5libが必要なので注意。

    strict・tmp_pathはキーワード引数での指定を推奨する。flask/quart/fastapi間で
    位置引数順を揃えているが、将来的な引数追加時の互換性のため。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type
        strict: Trueの場合、HTML5の仕様に従ったパースを行う
        tmp_path: 一時ファイルを保存するディレクトリ

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスボディ (bs4.BeautifulSoup)

    """
    response_body = response.text
    _core.assert_html_core(
        response_body,
        response.content,
        response.status_code,
        _content_type(response),
        status_code,
        content_type,
        strict,
        tmp_path,
    )
    return response_body


def assert_json(
    response: httpx.Response,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "application/json",
) -> typing.Any:
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
    return _core.assert_json_core(response_body, response.status_code, _content_type(response), status_code, content_type)


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
    _core.assert_xml_core(response_body, response.status_code, _content_type(response), status_code, content_type)
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
    _core.assert_sse_core(response.status_code, _content_type(response), status_code)
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
    _core.assert_response_core(response.status_code, status_code)
    return response
