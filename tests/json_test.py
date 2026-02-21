"""テストコード。"""

import io
import pathlib

import pytest

import pytilpack.json


def test_load_not_exist(tmp_path: pathlib.Path) -> None:
    # pylint: disable=use-implicit-booleaness-not-comparison
    assert pytilpack.json.load(tmp_path / "not_exist.json") == {}


def test_load_not_exist_strict(tmp_path: pathlib.Path) -> None:
    with pytest.raises(FileNotFoundError):
        pytilpack.json.load(tmp_path / "not_exist.json", strict=True)


def test_load_save(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "a.json"
    data = {"a": "💯", "c": 1}

    pytilpack.json.save(path, data)
    data2 = pytilpack.json.load(path)

    assert data["a"] == data2["a"]
    assert data["c"] == data2["c"]
    assert tuple(sorted(data)) == tuple(sorted(data2))


def test_load_save_io() -> None:
    """IO[str] / IO[bytes] での load/save のテスト。"""
    data = {"a": "💯", "c": 1}

    # StringIO で save → load
    buf = io.StringIO()
    pytilpack.json.save(buf, data)
    buf.seek(0)
    data2 = pytilpack.json.load(buf)
    assert data == data2

    # BytesIO で save → load
    buf_b = io.BytesIO()
    pytilpack.json.save(buf_b, data)
    buf_b.seek(0)
    data3 = pytilpack.json.load(buf_b)
    assert data == data3
