"""FastAPIのテストコード用アサーション関数。"""

import pathlib
import typing

import pytilpack._web_asserts as _core

__all__ = [
    "ResponseType",
    "assert_bytes",
    "assert_html",
    "assert_json",
    "assert_xml",
    "assert_sse",
    "assert_response",
]


class _HeadersType(typing.Protocol):
    """レスポンスヘッダーの構造的型。"""

    def get(self, key: str, default: typing.Any = None) -> typing.Any:
        """ヘッダー値を取得する。"""
        raise NotImplementedError


class ResponseType(typing.Protocol):
    """レスポンスの構造的型。

    starlette 1.2.0以降の`starlette/testclient.py`はhttpx2を優先してimportするため、
    `fastapi.testclient.TestClient`が返すレスポンスの型はhttpx2の導入有無で変わる。
    名目型で注釈すると一方の環境で静的型が不整合になるため、
    本モジュールが実際に使う属性だけを構造的に宣言してどちらでも成立させる。
    """

    @property
    def status_code(self) -> int:
        """ステータスコード。"""
        raise NotImplementedError

    @property
    def headers(self) -> _HeadersType:
        """レスポンスヘッダー。"""
        raise NotImplementedError

    @property
    def content(self) -> bytes:
        """レスポンスボディのbytes表現。"""
        raise NotImplementedError

    @property
    def text(self) -> str:
        """レスポンスボディの文字列表現。"""
        raise NotImplementedError


def _content_type(response: ResponseType) -> str | None:
    """レスポンスのContent-Typeヘッダー値を返す。"""
    return response.headers.get("content-type")


def assert_bytes(
    response: ResponseType,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = None,
) -> bytes:
    """レスポンスのステータスコードとContent-Typeを検証してボディをbytesで返す。

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
    response: ResponseType,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "__default__",
    strict: bool = False,
    tmp_path: pathlib.Path | None = None,
) -> str:
    """レスポンスを検証してHTMLボディを文字列で返す。html5libが必要。

    strict・tmp_pathはキーワード引数での指定を推奨する。flask/quart/fastapi間で
    位置引数順を揃えているが、将来の引数追加時の後方互換性を保つためである。

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
    response: ResponseType,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "application/json",
) -> typing.Any:
    """レスポンスを検証してJSONをデコードして返す。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスのJSONデコード結果

    """
    response_body = response.text
    return _core.assert_json_core(response_body, response.status_code, _content_type(response), status_code, content_type)


def assert_xml(
    response: ResponseType,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "__default__",
) -> str:
    """レスポンスを検証してXMLボディを文字列で返す。

    Args:
        response: レスポンス
        status_code: 期待するステータスコード
        content_type: 期待するContent-Type

    Raises:
        AssertionError: ステータスコードが異なる場合

    Returns:
        レスポンスボディ

    """
    response_body = response.text
    _core.assert_xml_core(response_body, response.status_code, _content_type(response), status_code, content_type)
    return response_body


def assert_sse[R: ResponseType](
    response: R,
    status_code: int = 200,
) -> R:
    """レスポンスのステータスコードとSSE用Content-Typeを検証して返す。

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


def assert_response[R: ResponseType](
    response: R,
    status_code: int = 200,
) -> R:
    """レスポンスのステータスコードを検証して返す。

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
