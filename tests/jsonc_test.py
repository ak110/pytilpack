"""pytilpack.jsonc のテスト。"""

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
