"""テストコード。"""

import pathlib

import pytilpack.yaml_


def test_load_not_exist(tmp_path: pathlib.Path) -> None:
    assert pytilpack.yaml_.load(tmp_path / "not_exist.yaml") == {}


def test_load_save(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "a.yaml"
    data = {"c": "💯\nあいうえお\n\n", "a": 1}

    pytilpack.yaml_.save(path, data)
    data2 = pytilpack.yaml_.load(path)

    assert data["a"] == data2["a"]
    assert data["c"] == data2["c"]
    assert tuple(sorted(data)) == tuple(sorted(data2))

    s = pathlib.Path(path).read_text("utf-8")
    assert s == "c: '💯\n\n  あいうえお\n\n\n  '\na: 1\n"
