"""テストコード。"""

import pathlib

import pytilpack.json_


def test_load_not_exist(tmp_path: pathlib.Path) -> None:
    assert pytilpack.json_.load(tmp_path / "not_exist.json") == {}


def test_load_save(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "a.json"
    data = {"a": "💯", "c": 1}

    pytilpack.json_.save(path, data)
    data2 = pytilpack.json_.load(path)

    assert data["a"] == data2["a"]
    assert data["c"] == data2["c"]
    assert tuple(sorted(data)) == tuple(sorted(data2))
