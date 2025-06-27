"""テストコード。"""

import pathlib

import pytilpack.csv


def test_read_to_dict(tmp_path: pathlib.Path) -> None:
    """read_to_dict()のテスト。"""
    path = tmp_path / "test.csv"
    path.write_text("name,age\nAlice,20\nBob,30")

    result = pytilpack.csv.read_to_dict(path, ["name", "age"])
    assert result == [{"name": "Alice", "age": "20"}, {"name": "Bob", "age": "30"}]
