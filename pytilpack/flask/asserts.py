__lazy_modules__ = [
    "flask",
    "pathlib",
    "pytilpack._web_asserts",
    "pytilpack.python",
    "pytilpack.web",
    "typing",
    "werkzeug.test",
]

import pathlib
import typing

import flask
import werkzeug.test

import pytilpack._web_asserts as _core
import pytilpack.python
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


def assert_bytes(
    response: ResponseType,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = None,
) -> bytes:
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
    response_bytes = response.get_data()
    response_body = response_bytes.decode("utf-8")
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


def assert_json(
    response: ResponseType,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "application/json",
) -> typing.Any:
    response_body = response.get_data().decode("utf-8")
    return _core.assert_json_core(response_body, response.status_code, response.content_type, status_code, content_type)


def assert_xml(
    response: ResponseType,
    status_code: int = 200,
    content_type: str | typing.Iterable[str] | None = "__default__",
) -> str:
    response_body = response.get_data().decode("utf-8")
    _core.assert_xml_core(response_body, response.status_code, response.content_type, status_code, content_type)
    return response_body


def assert_sse(
    response: ResponseType,
    status_code: int = 200,
) -> ResponseType:
    _core.assert_sse_core(response.status_code, response.content_type, status_code)
    return response


def assert_response(
    response: ResponseType,
    status_code: int = 200,
) -> ResponseType:
    _core.assert_response_core(response.status_code, status_code)
    return response


@pytilpack.python.deprecated("Use pytilpack.web.check_status_code instead.")
def check_status_code(status_code: int, valid_status_code: int) -> None:
    pytilpack.web.check_status_code(status_code, valid_status_code)


@pytilpack.python.deprecated("Use pytilpack.web.check_content_type instead.")
def check_content_type(content_type: str, valid_content_types: str | typing.Iterable[str] | None) -> None:
    pytilpack.web.check_content_type(content_type, valid_content_types)
