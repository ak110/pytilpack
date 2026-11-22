from __future__ import annotations

__lazy_modules__ = ["defusedxml.ElementTree", "json", "pathlib", "pytilpack.pytest", "pytilpack.web", "typing"]

import json
import pathlib
import typing

import defusedxml.ElementTree

import pytilpack.pytest
import pytilpack.web


def assert_bytes_core(
    response_body: bytes,
    status_code_value: int,
    content_type_value: str | None,
    expected_status_code: int,
    expected_content_type: str | typing.Iterable[str] | None,
) -> None:
    with pytilpack.pytest.AssertBlock(response_body, suffix=".txt"):
        pytilpack.web.check_status_code(status_code_value, expected_status_code)
        pytilpack.web.check_content_type(typing.cast(str, content_type_value), expected_content_type)


def assert_html_core(
    response_text: str,
    response_bytes: bytes,
    status_code_value: int,
    content_type_value: str | None,
    expected_status_code: int,
    expected_content_type: str | typing.Iterable[str] | None,
    strict: bool,
    tmp_path: pathlib.Path | None,
) -> None:
    if expected_content_type == "__default__":
        expected_content_type = ["text/html", "application/xhtml+xml"]

    with pytilpack.pytest.AssertBlock(response_text, suffix=".html", tmp_path=tmp_path):
        pytilpack.web.check_status_code(status_code_value, expected_status_code)
        pytilpack.web.check_content_type(typing.cast(str, content_type_value), expected_content_type)
        pytilpack.web.check_html(response_bytes, strict=strict)


def assert_json_core(
    response_text: str,
    status_code_value: int,
    content_type_value: str | None,
    expected_status_code: int,
    expected_content_type: str | typing.Iterable[str] | None,
) -> typing.Any:
    data: typing.Any
    with pytilpack.pytest.AssertBlock(response_text, suffix=".json"):
        pytilpack.web.check_status_code(status_code_value, expected_status_code)
        pytilpack.web.check_content_type(typing.cast(str, content_type_value), expected_content_type)
        try:
            data = json.loads(response_text)
        except Exception as e:
            raise AssertionError(f"JSONエラー: {e}") from e
    return data


def assert_xml_core(
    response_text: str,
    status_code_value: int,
    content_type_value: str | None,
    expected_status_code: int,
    expected_content_type: str | typing.Iterable[str] | None,
) -> None:
    if expected_content_type == "__default__":
        expected_content_type = ["text/xml", "application/xml"]

    with pytilpack.pytest.AssertBlock(response_text, suffix=".xml"):
        pytilpack.web.check_status_code(status_code_value, expected_status_code)
        pytilpack.web.check_content_type(typing.cast(str, content_type_value), expected_content_type)
        try:
            _ = defusedxml.ElementTree.fromstring(response_text)
        except Exception as e:
            raise AssertionError(f"XMLエラー: {e}") from e


def assert_sse_core(
    status_code_value: int,
    content_type_value: str | None,
    expected_status_code: int,
) -> None:
    pytilpack.web.check_status_code(status_code_value, expected_status_code)
    pytilpack.web.check_content_type(typing.cast(str, content_type_value), "text/event-stream")


def assert_response_core(
    status_code_value: int,
    expected_status_code: int,
) -> None:
    pytilpack.web.check_status_code(status_code_value, expected_status_code)
