"""Flask/Quart/FastAPI向けasserts.pyの共通実装（private）。

`pytilpack.flask.asserts` / `pytilpack.quart.asserts` / `pytilpack.fastapi.asserts`で
重複していた`assert_bytes`・`assert_html`・`assert_json`・`assert_xml`・`assert_sse`・
`assert_response`のコアロジックを集約する。

差分はレスポンス取得APIのみ（flask: `response.get_data()`、quart: `await response.get_data()`、
fastapi: `response.content`）。各フレームワーク側のラッパーからテキスト/バイト列を渡して呼び出す。
"""

from __future__ import annotations

import json
import pathlib
import typing
import xml.etree.ElementTree as ET

import pytilpack.pytest
import pytilpack.web


def assert_bytes_core(
    response_body: bytes,
    status_code_value: int,
    content_type_value: str | None,
    expected_status_code: int,
    expected_content_type: str | typing.Iterable[str] | None,
) -> None:
    """assert_bytesの共通チェック部分。

    `response.get_data()` / `response.content`等でbytesを取得済みの前提。
    """
    with pytilpack.pytest.AssertBlock(response_body, suffix=".txt"):  # bin では開けないため txt として扱う
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
    """assert_htmlの共通チェック部分。"""
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
    """assert_jsonの共通チェック部分。JSONデコード結果を返す。"""
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
    """assert_xmlの共通チェック部分。"""
    if expected_content_type == "__default__":
        expected_content_type = ["text/xml", "application/xml"]

    with pytilpack.pytest.AssertBlock(response_text, suffix=".xml"):
        pytilpack.web.check_status_code(status_code_value, expected_status_code)
        pytilpack.web.check_content_type(typing.cast(str, content_type_value), expected_content_type)
        try:
            _ = ET.fromstring(response_text)
        except Exception as e:
            raise AssertionError(f"XMLエラー: {e}") from e


def assert_sse_core(
    status_code_value: int,
    content_type_value: str | None,
    expected_status_code: int,
) -> None:
    """assert_sseの共通チェック部分。"""
    pytilpack.web.check_status_code(status_code_value, expected_status_code)
    pytilpack.web.check_content_type(typing.cast(str, content_type_value), "text/event-stream")


def assert_response_core(
    status_code_value: int,
    expected_status_code: int,
) -> None:
    """assert_responseの共通チェック部分。"""
    pytilpack.web.check_status_code(status_code_value, expected_status_code)
