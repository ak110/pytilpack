"""FastAPI関連のユーティリティ。"""

import io
import logging
import typing

import httpx

logger = logging.getLogger(__name__)


def assert_bytes(response: httpx.Response, status_code: int = 200) -> bytes:
    """fastapiのテストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスボディ

    """
    response_body = response.content

    # ステータスコードチェック
    if response.status_code != status_code:
        logger.info(
            f"ステータスコードエラー: {response.status_code} != {status_code}\n\n{response_body!r}"
        )
        raise AssertionError(
            f"ステータスコードエラー: {response.status_code} != {status_code})"
        )

    return response_body


def assert_html(response: httpx.Response, status_code: int = 200) -> str:
    """fastapiのテストコード用。

    html5libが必要なので注意。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスボディ (bs4.BeautifulSoup)

    """
    import html5lib

    response_body = response.text

    # HTMLのチェック
    parser = html5lib.HTMLParser(strict=True, debug=True)
    try:
        _ = parser.parse(io.BytesIO(response.content))
    except html5lib.html5parser.ParseError as e:
        logger.info(f"HTMLエラー: {e}\n\n{response_body}")
        raise AssertionError(f"HTMLエラー: {e}") from e

    # ステータスコードチェック
    if response.status_code != status_code:
        logger.info(
            f"ステータスコードエラー: {response.status_code} != {status_code}\n\n{response_body}"
        )
        raise AssertionError(
            f"ステータスコードエラー: {response.status_code} != {status_code})"
        )

    return response_body


def assert_json(
    response: httpx.Response, status_code: int = 200
) -> dict[str, typing.Any]:
    """fastapiのテストコード用。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスのjson

    """
    response_body = response.text

    # ステータスコードチェック
    if response.status_code != status_code:
        logger.info(
            f"ステータスコードエラー: {response.status_code} != {status_code}\n\n{response_body}"
        )
        raise AssertionError(
            f"ステータスコードエラー: {response.status_code} != {status_code})"
        )

    return response.json()
