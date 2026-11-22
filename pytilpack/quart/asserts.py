__lazy_modules__ = ["pathlib", "pytilpack._web_asserts", "quart", "typing"]

import pathlib
import typing

import quart

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

ResponseType = quart.Response | typing.Awaitable[quart.Response]


async def assert_bytes(
    response: ResponseType,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = None,
) -> bytes:
    response = await _get_response(response)
    response_body = await response.get_data(as_text=False)
    _core.assert_bytes_core(response_body, response.status_code, response.content_type, status_code, content_type)
    return response_body


async def assert_html(
    response: ResponseType,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "__default__",
    strict: bool = False,
    tmp_path: pathlib.Path | None = None,
) -> str:
    response = await _get_response(response)
    response_body = await response.get_data(as_text=True)
    response_bytes = await response.get_data(as_text=False)
    # arid: disable
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
    # arid: enable


async def assert_json(
    response: ResponseType,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "application/json",
) -> typing.Any:
    response = await _get_response(response)
    response_body = await response.get_data(as_text=True)
    return _core.assert_json_core(response_body, response.status_code, response.content_type, status_code, content_type)


async def assert_xml(
    response: ResponseType,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "__default__",
) -> str:
    response = await _get_response(response)
    response_body = await response.get_data(as_text=True)
    _core.assert_xml_core(response_body, response.status_code, response.content_type, status_code, content_type)
    return response_body


async def assert_sse(
    response: ResponseType,
    status_code: int = 200,
) -> quart.Response:
    response = await _get_response(response)
    _core.assert_sse_core(response.status_code, response.content_type, status_code)
    return response


async def assert_response(
    response: ResponseType,
    status_code: int = 200,
) -> quart.Response:
    response = await _get_response(response)
    _core.assert_response_core(response.status_code, status_code)
    return response


async def _get_response(response: ResponseType) -> quart.Response:
    if isinstance(response, typing.Awaitable):
        return await response
    return response
