import io
import pathlib

import yaml

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
    assert s == "c: |+\n  💯\n  あいうえお\n\na: 1\n"


def test_load_all_not_exist(tmp_path: pathlib.Path) -> None:
    # pylint: disable=use-implicit-booleaness-not-comparison
    assert pytilpack.yaml.load_all(tmp_path / "not_exist.yaml") == []


def test_load_all_save_all(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "a.yaml"
    data = [{"key": "value1", "num": 1}, {"key": "value2", "num": 2}]

    pytilpack.yaml.save_all(path, data)
    assert list(yaml.safe_load_all(path.read_text(encoding="utf-8"))) == data

    path.write_text("key: value1\nnum: 1\n---\nkey: value2\nnum: 2\n", encoding="utf-8")
    assert pytilpack.yaml.load_all(path) == data


def test_load_save_io() -> None:
    data = {"key": "💯", "num": 1}

    buf = io.StringIO()
    pytilpack.yaml.save(buf, data)
    buf.seek(0)
    data2 = pytilpack.yaml.load(buf)
    assert data == data2

    buf_b = io.BytesIO()
    pytilpack.yaml.save(buf_b, data)
    buf_b.seek(0)
    data3 = pytilpack.yaml.load(buf_b)
    assert data == data3


def test_block_scalar() -> None:
    assert pytilpack.yaml.dumps({"key": "line1\nline2\n"}) == "key: |\n  line1\n  line2\n"
    assert pytilpack.yaml.dumps({"key": "line1\ttab\nline2\n"}) == 'key: "line1\\ttab\\nline2\\n"\n'
    assert pytilpack.yaml.dumps({"key": "line1 \nline2\n"}) == 'key: "line1 \\nline2\\n"\n'
    assert pytilpack.yaml.dumps({"key": "line1\r\nline2\n"}) == 'key: "line1\\r\\nline2\\n"\n'
    assert pytilpack.yaml.dumps({"key": "line1\nline2\0null\n"}) == 'key: "line1\\nline2\\0null\\n"\n'
    assert pytilpack.yaml.dumps({"key": "only at end\n"}) == "key: 'only at end\n\n  '\n"
    assert pytilpack.yaml.dumps({"key": "no newline"}) == "key: no newline\n"


def test_load_all_save_all_io() -> None:
    data = [{"key": "value1"}, {"key": "value2"}]

    buf = io.StringIO()
    pytilpack.yaml.save_all(buf, data)
    buf.seek(0)
    data2 = pytilpack.yaml.load_all(buf)
    assert data == data2

    buf_b = io.BytesIO()
    pytilpack.yaml.save_all(buf_b, data)
    buf_b.seek(0)
    data3 = pytilpack.yaml.load_all(buf_b)
    assert data == data3
