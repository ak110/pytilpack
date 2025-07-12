"""Flaskのテストコード用アサーション関数。"""

import json
import logging
import pathlib
import typing
import warnings
import xml.etree.ElementTree as ET

import pytilpack.pytest
import pytilpack.web

logger = logging.getLogger(__name__)


def assert_bytes(
    response,
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
    response,
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
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスボディ (bs4.BeautifulSoup)

    """
    response_body = response.get_data().decode("utf-8")

    try:
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        if content_type == "__default__":
            content_type = ["text/html", "application/xhtml+xml"]
        pytilpack.web.check_content_type(response.content_type, content_type)

        # HTMLのチェック
        pytilpack.web.check_html(response.get_data(), strict=strict)
    except AssertionError as e:
        tmp_file_path = pytilpack.pytest.create_temp_view(tmp_path, response_body, ".html")
        raise AssertionError(f"{e} (HTML: {tmp_file_path} )") from e

    return response_body


def assert_json(
    response,
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
    response_body = response.get_data().decode("utf-8")

    try:
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        pytilpack.web.check_content_type(response.content_type, content_type)

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
    response,
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

    try:
        # ステータスコードチェック
        pytilpack.web.check_status_code(response.status_code, status_code)

        # Content-Typeチェック
        if content_type == "__default__":
            content_type = ["text/xml", "application/xml"]
        pytilpack.web.check_content_type(response.content_type, content_type)

        # XMLのチェック
        try:
            _ = ET.fromstring(response_body)
        except Exception as e:
            raise AssertionError(f"XMLエラー: {e}") from e
    except AssertionError as e:
        logger.info(f"{e}\n\n{response_body!r}")
        raise e

    return response_body


def check_status_code(status_code: int, valid_status_code: int) -> None:
    """deprecated."""
    warnings.warn(
        "pytilpack.flask_.check_status_code is deprecated. Use pytilpack.web.check_status_code instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    pytilpack.web.check_status_code(status_code, valid_status_code)


def check_content_type(content_type: str, valid_content_types: str | typing.Iterable[str] | None) -> None:
    """deprecated."""
    warnings.warn(
        "pytilpack.flask_.check_content_type is deprecated. Use pytilpack.web.check_content_type instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    pytilpack.web.check_content_type(content_type, valid_content_types)
