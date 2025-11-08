"""テストコード。"""

import pathlib

import pytest

import pytilpack.asyncio


@pytest.mark.asyncio
async def test_file_operations(tmp_path: pathlib.Path) -> None:
    """ファイル操作のテスト。"""
    # テストファイルのパス
    text_file = tmp_path / "test.txt"
    bytes_file = tmp_path / "test.bin"

    # テストデータ
    test_text = "Hello, World!\n日本語テスト"
    test_bytes = b"Hello, World!\x00\x01\x02"

    # write_text のテスト
    await pytilpack.asyncio.write_text(text_file, test_text)
    assert text_file.exists()

    # read_text のテスト
    result_text = await pytilpack.asyncio.read_text(text_file)
    assert result_text == test_text

    # write_bytes のテスト
    await pytilpack.asyncio.write_bytes(bytes_file, test_bytes)
    assert bytes_file.exists()

    # read_bytes のテスト
    result_bytes = await pytilpack.asyncio.read_bytes(bytes_file)
    assert result_bytes == test_bytes


@pytest.mark.asyncio
async def test_json_operations(tmp_path: pathlib.Path) -> None:
    """JSON操作のテスト。"""
    json_file = tmp_path / "test.json"

    # テストデータ
    test_data = {"name": "テスト", "value": 42, "list": [1, 2, 3], "nested": {"key": "value"}}

    # write_json のテスト
    await pytilpack.asyncio.write_json(json_file, test_data)
    assert json_file.exists()

    # read_json のテスト
    result = await pytilpack.asyncio.read_json(json_file)
    assert result == test_data

    # 存在しないファイルの読み込み（空のdictを返す）
    nonexistent_file = tmp_path / "nonexistent.json"
    result = await pytilpack.asyncio.read_json(nonexistent_file)
    assert result == {}


@pytest.mark.asyncio
async def test_json_operations_with_options(tmp_path: pathlib.Path) -> None:
    """JSONオプションのテスト。"""
    json_file = tmp_path / "test_options.json"

    test_data = {"z": 1, "a": 2, "japanese": "日本語"}

    # sort_keys=Trueでの書き込み
    await pytilpack.asyncio.write_json(json_file, test_data, sort_keys=True, indent=2)

    # ファイル内容を確認
    content = await pytilpack.asyncio.read_text(json_file)
    lines = content.strip().split("\n")
    assert '"a": 2' in lines[1]  # aが最初に来る
    assert '"japanese": "日本語"' in lines[2]
    assert '"z": 1' in lines[3]  # zが最後に来る

    # 読み込み確認
    result = await pytilpack.asyncio.read_json(json_file)
    assert result == test_data


@pytest.mark.asyncio
async def test_file_operations_with_encoding(tmp_path: pathlib.Path) -> None:
    """エンコーディングとエラーハンドリングのテスト。"""
    test_file = tmp_path / "test_encoding.txt"
    test_text = "Hello, 日本語"

    # UTF-8での書き込み・読み込み
    await pytilpack.asyncio.write_text(test_file, test_text, encoding="utf-8")
    result = await pytilpack.asyncio.read_text(test_file, encoding="utf-8")
    assert result == test_text

    # Shift_JISでの書き込み・読み込み
    await pytilpack.asyncio.write_text(test_file, test_text, encoding="shift_jis")
    result = await pytilpack.asyncio.read_text(test_file, encoding="shift_jis")
    assert result == test_text

    # errorsパラメータのテスト（ignore）
    await pytilpack.asyncio.write_text(test_file, "Hello\udc80World", encoding="utf-8", errors="ignore")
    result = await pytilpack.asyncio.read_text(test_file, encoding="utf-8")
    assert result == "HelloWorld"
