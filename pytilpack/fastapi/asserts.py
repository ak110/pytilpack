__lazy_modules__ = ["pathlib", "pytilpack._web_asserts", "typing"]

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
    def get(self, key: str, /) -> typing.Any:
        raise NotImplementedError


# starlette 1.2.0以降のTestClientはhttpx2を優先してimportし、返すレスポンスの型がhttpx2の導入有無で変わるため、
# 使う属性だけを構造的に宣言してどちらの環境でも型を成立させる。
class ResponseType(typing.Protocol):
    @property
    def status_code(self) -> int:
        raise NotImplementedError

    @property
    def headers(self) -> _HeadersType:
        raise NotImplementedError

    @property
    def content(self) -> bytes:
        raise NotImplementedError

    @property
    def text(self) -> str:
        raise NotImplementedError


def _content_type(response: ResponseType) -> str | None:
    return response.headers.get("content-type")


def assert_bytes(
    response: ResponseType,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = None,
) -> bytes:
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
    response_body = response.text
    return _core.assert_json_core(response_body, response.status_code, _content_type(response), status_code, content_type)


def assert_xml(
    response: ResponseType,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "__default__",
) -> str:
    response_body = response.text
    _core.assert_xml_core(response_body, response.status_code, _content_type(response), status_code, content_type)
    return response_body


def assert_sse[R: ResponseType](
    response: R,
    status_code: int = 200,
) -> R:
    _core.assert_sse_core(response.status_code, _content_type(response), status_code)
    return response


def assert_response[R: ResponseType](
    response: R,
    status_code: int = 200,
) -> R:
    _core.assert_response_core(response.status_code, status_code)
    return response
