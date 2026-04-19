"""Flaskのテストコード用アサーション関数。"""

import pathlib
import typing
import warnings

import flask
import werkzeug.test

import pytilpack._web_asserts as _core
import pytilpack.web

__all__ = [
    "ResponseType",
    "assert_bytes",
    "assert_html",
    "assert_json",
    "assert_xml",
    "assert_sse",
    "assert_response",
    "check_status_code",
    "check_content_type",
]

ResponseType = flask.Response | werkzeug.test.TestResponse
"""レスポンスの型。"""


def assert_bytes(
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
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスボディ

    """
    response_body = response.get_data()
    _core.assert_bytes_core(response_body, response.status_code, response.content_type, status_code, content_type)
    return response_body


def assert_html(
    response: ResponseType,
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
    response_bytes = response.get_data()
    response_body = response_bytes.decode("utf-8")
    _core.assert_html_core(
        response_body,
        response_bytes,
        response.status_code,
        response.content_type,
        status_code,
        content_type,
        strict,
        tmp_path,
    )
    return response_body


def assert_json(
    response: ResponseType,
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
    response_body = response.get_data().decode("utf-8")
    return _core.assert_json_core(response_body, response.status_code, response.content_type, status_code, content_type)


def assert_xml(
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
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスのxml

    """
    response_body = response.get_data().decode("utf-8")
    _core.assert_xml_core(response_body, response.status_code, response.content_type, status_code, content_type)
    return response_body


def assert_sse(
    response: ResponseType,
    status_code: int = 200,
) -> ResponseType:
    """テストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード

    Raises:
        AssertionError: ステータスコードが異なる場合、またはContent-Typeが異なる場合

    Returns:
        レスポンス

    """
    _core.assert_sse_core(response.status_code, response.content_type, status_code)
    return response


def assert_response(
    response: ResponseType,
    status_code: int = 200,
) -> ResponseType:
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


def check_status_code(status_code: int, valid_status_code: int) -> None:
    """Deprecated."""
    warnings.warn(
        "pytilpack.flask_.check_status_code is deprecated. Use pytilpack.web.check_status_code instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    pytilpack.web.check_status_code(status_code, valid_status_code)


def check_content_type(content_type: str, valid_content_types: str | typing.Iterable[str] | None) -> None:
    """Deprecated."""
    warnings.warn(
        "pytilpack.flask_.check_content_type is deprecated. Use pytilpack.web.check_content_type instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    pytilpack.web.check_content_type(content_type, valid_content_types)
