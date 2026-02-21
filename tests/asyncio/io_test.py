"""テストコード。"""

import datetime
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
async def test_jsonc_operations(tmp_path: pathlib.Path) -> None:
    # read_jsonc
    jsonc_file = tmp_path / "test.jsonc"
    await pytilpack.asyncio.write_text(
        jsonc_file,
        '{\n  // comment\n  "a": 1,\n  "b": [1, 2,],\n}\n',
    )
    assert await pytilpack.asyncio.read_jsonc(jsonc_file) == {"a": 1, "b": [1, 2]}


@pytest.mark.asyncio
async def test_yaml_operations(tmp_path: pathlib.Path) -> None:
    # YAML
    yaml_file = tmp_path / "test.yaml"
    yaml_data = {"a": 1, "b": [1, 2]}
    await pytilpack.asyncio.write_yaml(yaml_file, yaml_data)
    assert await pytilpack.asyncio.read_yaml(yaml_file) == yaml_data

    yaml_all_file = tmp_path / "test_all.yaml"
    yaml_all_data = [{"a": 1}, {"b": 2}]
    await pytilpack.asyncio.write_yaml_all(yaml_all_file, yaml_all_data)
    assert await pytilpack.asyncio.read_yaml_all(yaml_all_file) == yaml_all_data

    # delete_old_files
    old_root = tmp_path / "old"
    old_root.mkdir()
    old_file = old_root / "old.txt"
    await pytilpack.asyncio.write_text(old_file, "old")
    before = datetime.datetime.now() + datetime.timedelta(days=1)
    await pytilpack.asyncio.delete_old_files(old_root, before)
    assert not old_file.exists()


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


@pytest.mark.asyncio
async def test_asyncio_io_helpers(tmp_path: pathlib.Path) -> None:
    """補助関数の正常系テスト。"""
    # append_text / append_bytes
    text_file = tmp_path / "append.txt"
    bytes_file = tmp_path / "append.bin"
    await pytilpack.asyncio.write_text(text_file, "hello")
    await pytilpack.asyncio.append_text(text_file, " world")
    assert await pytilpack.asyncio.read_text(text_file) == "hello world"

    await pytilpack.asyncio.write_bytes(bytes_file, b"\x01\x02")
    await pytilpack.asyncio.append_bytes(bytes_file, b"\x03")
    assert await pytilpack.asyncio.read_bytes(bytes_file) == b"\x01\x02\x03"

    # delete_file
    delete_file = tmp_path / "delete.txt"
    await pytilpack.asyncio.write_text(delete_file, "x")
    assert delete_file.exists()
    await pytilpack.asyncio.delete_file(delete_file)
    assert not delete_file.exists()

    # get_size
    size_file = tmp_path / "size.bin"
    await pytilpack.asyncio.write_bytes(size_file, b"\x00\x01\x02\x03")
    assert await pytilpack.asyncio.get_size(size_file) == 4

    # delete_empty_dirs
    empty_root = tmp_path / "empty_root"
    empty_child = empty_root / "child"
    empty_child.mkdir(parents=True)
    await pytilpack.asyncio.delete_empty_dirs(empty_root)
    assert empty_root.exists()
    assert not empty_child.exists()

    # sync
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    await pytilpack.asyncio.write_text(src_dir / "file.txt", "data")
    await pytilpack.asyncio.sync(src_dir, dst_dir)
    assert (dst_dir / "file.txt").exists()

    await pytilpack.asyncio.write_text(dst_dir / "extra.txt", "extra")
    await pytilpack.asyncio.sync(src_dir, dst_dir, delete=True)
    assert not (dst_dir / "extra.txt").exists()
