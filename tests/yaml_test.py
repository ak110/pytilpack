"""テストコード。"""

import pathlib

import pytilpack.yaml


def test_load_not_exist(tmp_path: pathlib.Path) -> None:
    assert pytilpack.yaml.load(tmp_path / "not_exist.yaml") == {}


def test_load_save(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "a.yaml"
    data = {"c": "💯\nあいうえお\n\n", "a": 1}

    pytilpack.yaml.save(path, data)
    data2 = pytilpack.yaml.load(path)

    assert data["a"] == data2["a"]
    assert data["c"] == data2["c"]
    assert tuple(sorted(data)) == tuple(sorted(data2))

    s = pathlib.Path(path).read_text("utf-8")
    assert s == "c: '💯\n\n  あいうえお\n\n\n  '\na: 1\n"


def test_load_all_not_exist(tmp_path: pathlib.Path) -> None:
    # pylint: disable=use-implicit-booleaness-not-comparison
    assert pytilpack.yaml.load_all(tmp_path / "not_exist.yaml") == []


def test_load_all_save_all(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "a.yaml"
    data = [{"key": "value1", "num": 1}, {"key": "value2", "num": 2}]

    pytilpack.yaml.save_all(path, data)
    data2 = pytilpack.yaml.load_all(path)

    assert len(data2) == 2
    assert data[0] == data2[0]
    assert data[1] == data2[1]
