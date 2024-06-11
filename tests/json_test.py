"""テストコード。"""

import pytilpack.json_


def test_load_not_exist(tmpdir):
    assert pytilpack.json_.load(tmpdir / "not_exist.json") == {}


def test_load_save(tmpdir):
    path = str(tmpdir / "a.json")
    data = {"a": "💯", "c": 1}

    pytilpack.json_.save(path, data)
    data2 = pytilpack.json_.load(path)

    assert data["a"] == data2["a"]
    assert data["c"] == data2["c"]
    assert tuple(sorted(data)) == tuple(sorted(data2))
