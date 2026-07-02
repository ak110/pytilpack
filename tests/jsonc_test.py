"""pytilpack.jsonc のテスト。"""

import io
import pathlib

import pytest

import pytilpack.jsonc


@pytest.mark.parametrize(
    "text,expected",
    [
        # 行コメント
        ('{"a": 1} // comment', {"a": 1}),
        # ブロックコメント
        ('{"a": /* comment */ 1}', {"a": 1}),
        # 複数行ブロックコメント
        ('{\n/* comment\n   line2 */\n"a": 1}', {"a": 1}),
        # 文字列内のコメント記号はそのまま
        ('{"a": "//not a comment"}', {"a": "//not a comment"}),
        ('{"a": "/* not a comment */"}', {"a": "/* not a comment */"}),
        # コメントなし
        ('{"a": 1, "b": "hello"}', {"a": 1, "b": "hello"}),
        # trailing comma (object)
        ('{"a": 1,}', {"a": 1}),
        # trailing comma (array)
        ('{"a": [1, 2,]}', {"a": [1, 2]}),
        # trailing comma + コメント間
        ('{"a": 1, // last\n}', {"a": 1}),
        # 文字列内の ",}" はそのまま
        ('{"a": ",}"}', {"a": ",}"}),
    ],
)
def test_loads(text: str, expected: dict) -> None:
    """loadsのテスト。"""
    assert pytilpack.jsonc.loads(text) == expected


def test_load(tmp_path: pathlib.Path) -> None:
    """loadのテスト。"""
    p = tmp_path / "test.jsonc"
    p.write_text('{\n  // comment\n  "key": "value"\n}\n', encoding="utf-8")
    assert pytilpack.jsonc.load(p) == {"key": "value"}

    # ファイルなし (strict=False)
    assert pytilpack.jsonc.load(tmp_path / "missing.jsonc") == {}

    # ファイルなし (strict=True)
    with pytest.raises(FileNotFoundError):
        pytilpack.jsonc.load(tmp_path / "missing.jsonc", strict=True)


def test_edit_preserves_comments_and_blank_lines() -> None:
    """editがコメント・空行・インデントを維持することを確認する。"""
    text = (
        "{\n"
        "  // トップの説明\n"
        '  "name": "old",\n'
        "\n"
        '  "config": {\n'
        "    /* ネストの説明 */\n"
        '    "port": 8080,\n'
        '    "debug": false\n'
        "  }\n"
        "}\n"
    )
    result = pytilpack.jsonc.edit(text, {("name",): "new", ("config", "port"): 9090})
    assert result == (
        "{\n"
        "  // トップの説明\n"
        '  "name": "new",\n'
        "\n"
        '  "config": {\n'
        "    /* ネストの説明 */\n"
        '    "port": 9090,\n'
        '    "debug": false\n'
        "  }\n"
        "}\n"
    )


def test_edit_array_index() -> None:
    """配列要素をインデックスで書き換えられることを確認する。"""
    text = '{"items": [\n  1, // first\n  2, // second\n  3, // third\n]}\n'
    result = pytilpack.jsonc.edit(text, {("items", 1): 20})
    assert result == '{"items": [\n  1, // first\n  20, // second\n  3, // third\n]}\n'


def test_edit_root_replacement() -> None:
    """空タプルパスでルート全体を差し替えられることを確認する。"""
    text = '// header\n{"a": 1}\n'
    result = pytilpack.jsonc.edit(text, {(): {"b": 2}})
    assert result == '// header\n{"b": 2}\n'


def test_edit_missing_key_raises() -> None:
    """存在しないパスはKeyErrorになることを確認する。"""
    with pytest.raises(KeyError):
        pytilpack.jsonc.edit('{"a": 1}', {("b",): 2})


def test_edit_type_mismatch_raises() -> None:
    """パスの途中で型が合わない場合はTypeErrorになることを確認する。"""
    with pytest.raises(TypeError):
        pytilpack.jsonc.edit('{"a": 1}', {("a", "b"): 2})


def test_edit_overlapping_paths_rejected() -> None:
    """包含関係を持つパスを同時指定した場合はValueErrorになることを確認する。"""
    with pytest.raises(ValueError):
        pytilpack.jsonc.edit(
            '{"a": {"b": 1}}',
            {("a",): {"c": 3}, ("a", "b"): 2},
        )


def test_edit_file(tmp_path: pathlib.Path) -> None:
    """edit_fileでファイルを差し替えられることを確認する。"""
    p = tmp_path / "config.jsonc"
    p.write_text('{\n  // note\n  "value": 1\n}\n', encoding="utf-8")
    pytilpack.jsonc.edit_file(p, {("value",): 42})
    assert p.read_text(encoding="utf-8") == '{\n  // note\n  "value": 42\n}\n'


def test_load_io() -> None:
    """IO[str] / IO[bytes] での load のテスト。"""
    text = '{\n  // comment\n  "key": "value"\n}\n'

    # StringIO
    buf = io.StringIO(text)
    assert pytilpack.jsonc.load(buf) == {"key": "value"}

    # BytesIO
    buf_b = io.BytesIO(text.encode("utf-8"))
    assert pytilpack.jsonc.load(buf_b) == {"key": "value"}
