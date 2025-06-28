"""テストコード。"""

import pathlib

import pytilpack.json


def test_load_not_exist(tmp_path: pathlib.Path) -> None:
    # pylint: disable=use-implicit-booleaness-not-comparison
    assert pytilpack.json.load(tmp_path / "not_exist.json") == {}


def test_load_save(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "a.json"
    data = {"a": "💯", "c": 1}

    pytilpack.json.save(path, data)
    data2 = pytilpack.json.load(path)

    assert data["a"] == data2["a"]
    assert data["c"] == data2["c"]
    assert tuple(sorted(data)) == tuple(sorted(data2))
